"""Content-hash cache for wiki-ingest source tracking.

Provides a reliable, platform-independent alternative to running `sha256sum`
in the skill. The agent calls `llm-wiki cache-check` / `cache-update`
instead of shelling out to sha256sum and manually parsing .manifest.json.

Manifest format (.manifest.json in the vault root). Keys are absolute
expanded paths and the created/updated split is required by DONE criterion 2
of the vault constitution (AGENTS.md):
{
  "sources": {
    "<abs-path>": {
      "content_hash": "<sha256-hex>",
      "ingested_at": "<ISO-8601>",
      "pages_created": ["<vault-relative-page-path>", ...],
      "pages_updated": ["<vault-relative-page-path>", ...]
    }
  }
}

This module is the single source of truth for that schema: the key form
(`canonical_key`), the timestamp field (`ingested_at`), and the new /
modified / unchanged classification (`check_sources`). `scripts/manifest.py`
calls in here rather than reimplementing any of it — two implementations
would eventually give two answers about whether a source needs re-ingesting.

Legacy spellings are read but never written, and are migrated the next time
their source is re-ingested:
  - `pages_produced` — the single list that predates the created/updated split.
  - `last_ingested`  — the old name for `ingested_at` on a *source* entry.
    Note the `projects` and `hermes` summary blocks have their own
    `last_ingested` field; that one is unrelated and stays as it is.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class SourceEntry(TypedDict, total=False):
    content_hash: str
    ingested_at: str
    pages_created: list[str]
    pages_updated: list[str]
    pages_produced: list[str]  # legacy single-list form, read-only
    last_ingested: str         # legacy name for ingested_at, read-only


class CheckResult(TypedDict):
    new: list[str]
    modified: list[str]
    unchanged: list[str]
    missing: list[str]   # in manifest but file no longer on disk


# Canonical spelling first, legacy second. Both are read; if an entry somehow
# carries both, `entry_time` takes the later value rather than a preferred key.
TIME_KEYS = ("ingested_at", "last_ingested")


def canonical_key(path: Path | str) -> str:
    """The one manifest key form: `~` and env vars expanded, then absolute.

    The manifest is keyed by the raw string, so `~/.claude/x.jsonl` and
    `/home/me/.claude/x.jsonl` are two entries for one file — and the lookup
    that misses the other form re-ingests a source that was already processed.
    """
    return os.path.abspath(os.path.expandvars(os.path.expanduser(str(path))))


def entry_time(entry: SourceEntry) -> str:
    """Newest ingest timestamp on an entry under any spelling. '' if none."""
    stamps = [str(entry[k]) for k in TIME_KEYS if entry.get(k)]  # type: ignore[literal-required]
    return max(stamps) if stamps else ""


class ManifestError(RuntimeError):
    """The manifest exists but cannot be read as a manifest.

    A RuntimeError so the CLI's top-level handler reports it as
    `error: <what>` and exits 1, rather than printing a traceback.
    """


def _manifest_path(vault: Path) -> Path:
    return vault / ".manifest.json"


def read_manifest_doc(vault: Path) -> dict:
    """The whole manifest document, or `{}` when the vault has none yet.

    A manifest that exists but will not parse is an error, never an empty one.
    Reading it as empty means `check_sources` reports every source as new — a
    silent full re-ingest — and the next save then overwrites the damaged file,
    taking the `projects` and `stats` blocks with it. A missing file is the
    one legitimately empty case: that is a fresh vault.
    """
    mp = _manifest_path(vault)
    if not mp.exists():
        return {}
    try:
        doc = json.loads(mp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{mp} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise ManifestError(f"cannot read {mp}: {exc}") from exc
    if not isinstance(doc, dict):
        raise ManifestError(f"{mp} must contain a JSON object")
    return doc


def write_manifest_doc(vault: Path, doc: dict) -> None:
    """Write the whole manifest via a temp file, then rename over the original.

    An interrupted in-place write leaves a truncated ledger — which the reader
    above then refuses, so one killed `cache-update` would block every later
    one. `os.replace` is atomic, so a reader sees either the whole old document
    or the whole new one.
    """
    path = _manifest_path(vault)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _load_manifest(vault: Path) -> dict[str, SourceEntry]:
    sources = read_manifest_doc(vault).get("sources", {})
    if not isinstance(sources, dict):
        raise ManifestError(f"{_manifest_path(vault)}: 'sources' must be a JSON object")
    return sources


def _save_manifest(vault: Path, sources: dict[str, SourceEntry]) -> None:
    # Reads the existing document first, so a damaged manifest stops the write
    # instead of being replaced by one holding nothing but `sources`.
    doc = read_manifest_doc(vault)
    doc["sources"] = sources
    write_manifest_doc(vault, doc)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Return the hex SHA-256 digest of *path* without loading it all into RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def sha256_dir(path: Path) -> str:
    """Stable SHA-256 over all files in a directory tree (sorted by relative path)."""
    h = hashlib.sha256()
    for fp in sorted(path.rglob("*")):
        if fp.is_file():
            rel = str(fp.relative_to(path))
            h.update(rel.encode())
            h.update(sha256_file(fp).encode())
    return h.hexdigest()


def compute_hash(path: Path) -> str:
    if path.is_dir():
        return sha256_dir(path)
    return sha256_file(path)


def _canonical_sources(raw: dict[str, SourceEntry]) -> dict[str, SourceEntry]:
    """Rekey a manifest canonically for lookup. Newest entry wins a collision.

    A vault that mixes `~`-relative and absolute keys holds two entries for one
    file. Repairing that on disk is `scripts/manifest.py normalize`; here we
    only need the reads to stop missing the other form.
    """
    canonical: dict[str, SourceEntry] = {}
    for key, entry in raw.items():
        ckey = canonical_key(key)
        rival = canonical.get(ckey)
        if rival is None or entry_time(entry) >= entry_time(rival):
            canonical[ckey] = entry
    return canonical


def check_sources(vault: Path, source_paths: list[Path]) -> CheckResult:
    """Classify each source as new / modified / unchanged vs. the manifest.

    Also reports manifest entries whose source file no longer exists on disk.
    Buckets hold the caller's own path strings; only the manifest lookup is
    canonicalised, so callers can match the results against what they passed in.
    """
    raw_sources = _load_manifest(vault)
    sources = _canonical_sources(raw_sources)
    result: CheckResult = {"new": [], "modified": [], "unchanged": [], "missing": []}

    for path in source_paths:
        key = str(path)
        if not path.exists():
            result["missing"].append(key)
            continue
        current_hash = compute_hash(path)
        entry = sources.get(canonical_key(path))
        if entry is None:
            result["new"].append(key)
        elif entry.get("content_hash") != current_hash:
            # Also covers entries predating content_hash: with nothing to
            # compare against, re-ingesting is the only answer that cannot be
            # wrong, and it backfills the hash.
            result["modified"].append(key)
        else:
            result["unchanged"].append(key)

    # Report manifest keys that no longer exist on disk (not in source_paths scan)
    checked = {canonical_key(p) for p in source_paths}
    for key in raw_sources:
        if canonical_key(key) not in checked and not Path(canonical_key(key)).exists():
            result["missing"].append(key)

    return result


def update_source(
    vault: Path,
    source_path: Path,
    *,
    pages_created: list[str] | None = None,
    pages_updated: list[str] | None = None,
) -> str:
    """Record the current hash of *source_path* in the manifest. Returns the hash.

    Keys are normalised to canonical absolute paths so a source recorded from
    one working directory — or under `~` — is still recognised from another.
    This write is also where legacy entries are migrated to the current schema.
    """
    sources = _load_manifest(vault)
    key = canonical_key(source_path)
    current_hash = compute_hash(source_path)

    # Collapse every spelling of this path into the canonical key. Leaving the
    # `~`-relative or relative duplicate behind would keep one file tracked
    # twice, and a later check could still read the stale copy.
    duplicates = [k for k in sources if canonical_key(k) == key]
    prior = [sources.pop(k) for k in duplicates]
    entry: SourceEntry = dict(max(prior, key=entry_time)) if prior else {}
    entry["content_hash"] = current_hash
    entry["ingested_at"] = datetime.now(timezone.utc).isoformat()
    entry.pop("last_ingested", None)  # legacy spelling; ingested_at supersedes it
    if pages_created is not None:
        entry["pages_created"] = pages_created
    if pages_updated is not None:
        entry["pages_updated"] = pages_updated
    if (pages_created is not None or pages_updated is not None):
        # The two-list form supersedes the legacy single list; keeping both
        # would leave two disagreeing records of the same ingest.
        entry.pop("pages_produced", None)

    sources[key] = entry
    _save_manifest(vault, sources)
    return current_hash


def hash_file(path: Path) -> str:
    """Just compute and return the hash — no manifest I/O."""
    return compute_hash(path)
