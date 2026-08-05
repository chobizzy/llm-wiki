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
        Report which scanned sources are new, modified or unchanged. Adds glob
        scanning and skip handling on top of `llm-wiki cache-check`, which does
        the classifying — see llm_wiki/cache.py.

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

# The schema — key form, timestamp field, classification — lives in
# llm_wiki.cache. Reimplementing any of it here would let the two drift and
# disagree about whether a source needs re-ingesting.
try:
    from llm_wiki.cache import (
        ManifestError, canonical_key, check_sources, entry_time, read_manifest_doc,
        write_manifest_doc,
    )
except ImportError:  # not pip-installed — fall back to the adjacent package
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from llm_wiki.cache import (
        ManifestError, canonical_key, check_sources, entry_time, read_manifest_doc,
        write_manifest_doc,
    )

MANIFEST_NAME = ".manifest.json"

PAGE_KEYS = ("pages_created", "pages_updated", "pages_produced")


def load_manifest(vault: Path) -> dict:
    """Return the whole manifest document, or an empty skeleton.

    Parsing lives in llm_wiki.cache. This only translates its failure into the
    SystemExit this script exits with everywhere else.
    """
    try:
        doc = read_manifest_doc(vault)
    except ManifestError as exc:
        raise SystemExit(f"error: {exc}")
    doc.setdefault("sources", {})
    return doc


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
        grouped.setdefault(canonical_key(raw_key), []).append((raw_key, entry))

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
    vault = Path(canonical_key(args.vault))
    if not vault.is_dir():
        raise SystemExit(f"error: vault not found: {vault}")

    doc = load_manifest(vault)
    before = doc["sources"]
    after, collisions = normalize_sources(before)

    rekeyed = sum(1 for k in before if k != canonical_key(k))
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
    write_manifest_doc(vault, doc)
    print(f"\nwrote {vault / MANIFEST_NAME}")
    return 0


def expand_scan(patterns: list[str], skips: list[str]) -> list[Path]:
    """Resolve glob patterns to canonical paths, dropping skipped substrings."""
    found: set[str] = set()
    for pattern in patterns:
        expanded = os.path.expandvars(os.path.expanduser(pattern))
        for hit in glob.glob(expanded, recursive=True):
            path = canonical_key(hit)
            if any(skip and skip in path for skip in skips):
                continue
            if os.path.isfile(path):
                found.add(path)
    return [Path(p) for p in sorted(found)]


def cmd_delta(args: argparse.Namespace) -> int:
    vault = Path(canonical_key(args.vault))
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

    # check_sources is the one classifier; this command only decides *which*
    # files to hand it. It canonicalises manifest keys on lookup, so a vault
    # still holding ~-relative keys resolves correctly here too.
    buckets = check_sources(vault, paths)

    if args.json:
        print(json.dumps(buckets, indent=2))
        return 0

    print(f"scanned  : {len(paths)} file(s)")
    for name in ("new", "modified", "unchanged"):
        print(f"{name:9}: {len(buckets[name])}")
    for name in ("new", "modified"):
        for item in buckets[name]:
            print(f"  {name:8} {item}")
    if buckets["missing"]:
        print(f"\n{len(buckets['missing'])} manifest entr(ies) no longer on disk "
              f"(outside this scan); `normalize` does not remove them.")
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
    try:
        return args.func(args)
    except ManifestError as exc:  # raised from inside check_sources
        raise SystemExit(f"error: {exc}")


if __name__ == "__main__":
    sys.exit(main())
