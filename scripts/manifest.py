#!/usr/bin/env python3
"""Canonicalise and query a vault's .manifest.json.

The manifest is keyed by the raw source-path string, so a file recorded once as
`~/.claude/projects/x.jsonl` and again as `/home/me/.claude/projects/x.jsonl` is
tracked twice. Delta checks then miss the other-form key and re-ingest a source
that was already processed.

Two commands:

    manifest.py normalize VAULT [--dry-run]
        Merge keys that expand to the same absolute path.

    manifest.py delta VAULT --scan GLOB [--scan GLOB ...] [--skip a,b]
        Report which scanned sources are new, modified, touched or unchanged,
        comparing against canonicalised manifest keys.

Both expand `~` and environment variables before comparing, which is the whole
point: an agent that skips that step re-ingests files it already has.

    python3 scripts/manifest.py normalize ~/Documents/my-wiki --dry-run
    python3 scripts/manifest.py delta ~/Documents/my-wiki \
        --scan "~/.claude/projects/*/memory/*.md"
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

# Hashing lives in llm_wiki.cache; reimplementing it here would let the two
# drift and disagree about whether a source changed.
try:
    from llm_wiki.cache import compute_hash
except ImportError:  # not pip-installed — fall back to the adjacent package
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from llm_wiki.cache import compute_hash

MANIFEST_NAME = ".manifest.json"

# wiki-status/SKILL.md documents `ingested_at`; llm_wiki.cache writes
# `last_ingested`. Both exist in real vaults, so read either and never assume.
TIME_KEYS = ("ingested_at", "last_ingested")
PAGE_KEYS = ("pages_created", "pages_updated", "pages_produced")


def canonical(raw: str) -> str:
    """Expand ~ and env vars, then absolutise. The one true key form."""
    return os.path.abspath(os.path.expandvars(os.path.expanduser(str(raw))))


def load_manifest(vault: Path) -> dict:
    """Return the whole manifest document, or an empty skeleton."""
    path = vault / MANIFEST_NAME
    if not path.exists():
        return {"sources": {}}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: {path} is not valid JSON: {exc}")
    except OSError as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}")
    if not isinstance(doc, dict):
        raise SystemExit(f"error: {path} must contain a JSON object")
    doc.setdefault("sources", {})
    return doc


def save_manifest(vault: Path, doc: dict) -> None:
    """Write via a temp file so an interrupted run cannot truncate the ledger."""
    path = vault / MANIFEST_NAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def entry_time(entry: dict) -> str:
    """Newest timestamp on an entry under any spelling. Empty string if none."""
    stamps = [str(entry[k]) for k in TIME_KEYS if entry.get(k)]
    return max(stamps) if stamps else ""


def merge_entries(entries: list[dict]) -> dict:
    """Fold colliding entries into one: newest wins, page lists union.

    Scalars come from the newest entry, but the page lists are unioned rather
    than overwritten. Dropping the older entry's pages_created would strand the
    provenance link that lets a re-ingest find the pages a source produced.
    """
    ordered = sorted(entries, key=entry_time)
    merged = dict(ordered[-1])
    for key in PAGE_KEYS:
        seen = {p for e in entries for p in e.get(key, []) or []}
        if seen:
            merged[key] = sorted(seen)
    return merged


def normalize_sources(sources: dict) -> tuple[dict, list[dict]]:
    """Rekey every source canonically. Returns (new_sources, collisions)."""
    grouped: dict[str, list[tuple[str, dict]]] = {}
    for raw_key, entry in sources.items():
        grouped.setdefault(canonical(raw_key), []).append((raw_key, entry))

    normalized: dict[str, dict] = {}
    collisions: list[dict] = []
    for key, members in sorted(grouped.items()):
        if len(members) == 1:
            normalized[key] = members[0][1]
            continue
        collisions.append({"canonical": key, "merged_from": [k for k, _ in members]})
        normalized[key] = merge_entries([e for _, e in members])
    return normalized, collisions


def cmd_normalize(args: argparse.Namespace) -> int:
    vault = Path(canonical(args.vault))
    if not vault.is_dir():
        raise SystemExit(f"error: vault not found: {vault}")

    doc = load_manifest(vault)
    before = doc["sources"]
    after, collisions = normalize_sources(before)

    rekeyed = sum(1 for k in before if k != canonical(k))
    print(f"manifest : {vault / MANIFEST_NAME}")
    print(f"entries  : {len(before)} -> {len(after)}")
    print(f"rekeyed  : {rekeyed}")
    print(f"merged   : {len(collisions)} collision(s)")
    for col in collisions:
        print(f"\n  {col['canonical']}")
        for raw in col["merged_from"]:
            print(f"    <- {raw}")

    if before == after:
        print("\nAlready canonical. Nothing to write.")
        return 0
    if args.dry_run:
        print("\nDry run: nothing written. Re-run without --dry-run to apply.")
        return 0

    doc["sources"] = after
    save_manifest(vault, doc)
    print(f"\nwrote {vault / MANIFEST_NAME}")
    return 0


def expand_scan(patterns: list[str], skips: list[str]) -> list[Path]:
    """Resolve glob patterns to canonical paths, dropping skipped substrings."""
    found: set[str] = set()
    for pattern in patterns:
        expanded = os.path.expandvars(os.path.expanduser(pattern))
        for hit in glob.glob(expanded, recursive=True):
            path = canonical(hit)
            if any(skip and skip in path for skip in skips):
                continue
            if os.path.isfile(path):
                found.add(path)
    return [Path(p) for p in sorted(found)]


def classify(path: Path, entry: dict | None) -> str:
    """new / modified / touched / unchanged for one scanned source.

    'touched' means the file's mtime moved but its content hash did not, which
    is the case worth reporting separately: re-ingesting it would burn tokens
    to produce identical pages.
    """
    if entry is None:
        return "new"
    stamp = entry_time(entry)
    recorded = entry.get("content_hash")
    if recorded:
        return "unchanged" if compute_hash(path) == recorded else "modified"
    # No hash on the entry (older manifest): mtime is all there is to go on.
    if not stamp:
        return "modified"
    mtime = _iso_mtime(path)
    return "touched" if mtime > stamp else "unchanged"


def _iso_mtime(path: Path) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def cmd_delta(args: argparse.Namespace) -> int:
    vault = Path(canonical(args.vault))
    if not vault.is_dir():
        raise SystemExit(f"error: vault not found: {vault}")

    skips = [s.strip() for s in (args.skip or "").split(",") if s.strip()]
    skips += [s.strip() for s in os.environ.get("WIKI_SKIP_PROJECTS", "").split(",")
              if s.strip()]

    paths = expand_scan(args.scan, skips)
    if not paths:
        raise SystemExit(
            "error: --scan matched no files. Check the pattern and quote it so "
            "the shell does not expand it first."
        )

    # Canonical lookup: the manifest on disk may still hold ~-relative keys.
    sources = {canonical(k): v for k, v in load_manifest(vault)["sources"].items()}
    buckets: dict[str, list[str]] = {
        "new": [], "modified": [], "touched": [], "unchanged": []
    }
    for path in paths:
        buckets[classify(path, sources.get(str(path)))].append(str(path))

    if args.json:
        print(json.dumps(buckets, indent=2))
        return 0

    print(f"scanned  : {len(paths)} file(s)")
    for name in ("new", "modified", "touched", "unchanged"):
        print(f"{name:9}: {len(buckets[name])}")
    for name in ("new", "modified"):
        for item in buckets[name]:
            print(f"  {name:8} {item}")
    if buckets["touched"]:
        print("\ntouched files have a newer mtime but identical content; skip them.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Canonicalise and query a vault's .manifest.json."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    norm = sub.add_parser("normalize", help="merge ~-relative and absolute keys")
    norm.add_argument("vault")
    norm.add_argument("--dry-run", action="store_true",
                      help="report what would change without writing")
    norm.set_defaults(func=cmd_normalize)

    delta = sub.add_parser("delta", help="classify scanned sources against the manifest")
    delta.add_argument("vault")
    delta.add_argument("--scan", action="append", required=True, metavar="GLOB",
                       help="glob of sources to check; repeatable, quote it")
    delta.add_argument("--skip", metavar="A,B",
                       help="comma-separated substrings to exclude "
                            "(added to WIKI_SKIP_PROJECTS)")
    delta.add_argument("--json", action="store_true", help="machine-readable output")
    delta.set_defaults(func=cmd_delta)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
