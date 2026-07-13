"""Content-hash cache for wiki-ingest source tracking.

Provides a reliable, platform-independent alternative to running `sha256sum`
in the skill. The agent calls `llm-wiki cache-check` / `cache-update`
instead of shelling out to sha256sum and manually parsing .manifest.json.

Manifest format (.manifest.json in the vault root):
{
  "sources": {
    "<abs-or-rel-path>": {
      "content_hash": "<sha256-hex>",
      "last_ingested": "<ISO-8601>",
      "pages_produced": ["<vault-relative-page-path>", ...]
    }
  }
}
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
    last_ingested: str
    pages_produced: list[str]


class CheckResult(TypedDict):
    new: list[str]
    modified: list[str]
    unchanged: list[str]
    missing: list[str]   # in manifest but file no longer on disk


def _manifest_path(vault: Path) -> Path:
    return vault / ".manifest.json"


def _load_manifest(vault: Path) -> dict[str, SourceEntry]:
    mp = _manifest_path(vault)
    if not mp.exists():
        return {}
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
        return data.get("sources", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _save_manifest(vault: Path, sources: dict[str, SourceEntry]) -> None:
    mp = _manifest_path(vault)
    existing: dict = {}
    if mp.exists():
        try:
            existing = json.loads(mp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    existing["sources"] = sources
    mp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


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


def check_sources(vault: Path, source_paths: list[Path]) -> CheckResult:
    """Classify each source as new / modified / unchanged vs. the manifest.

    Also reports manifest entries whose source file no longer exists on disk.
    """
    sources = _load_manifest(vault)
    result: CheckResult = {"new": [], "modified": [], "unchanged": [], "missing": []}

    for path in source_paths:
        key = str(path)
        if not path.exists():
            result["missing"].append(key)
            continue
        current_hash = compute_hash(path)
        entry = sources.get(key) or sources.get(os.path.abspath(key))
        if entry is None:
            result["new"].append(key)
        elif entry.get("content_hash") != current_hash:
            result["modified"].append(key)
        else:
            result["unchanged"].append(key)

    # Report manifest keys that no longer exist on disk (not in source_paths scan)
    checked = {str(p) for p in source_paths} | {os.path.abspath(p) for p in source_paths}
    for key in sources:
        if key not in checked and not Path(key).exists():
            result["missing"].append(key)

    return result


def update_source(
    vault: Path,
    source_path: Path,
    *,
    pages_produced: list[str] | None = None,
) -> str:
    """Record the current hash of *source_path* in the manifest. Returns the hash."""
    sources = _load_manifest(vault)
    key = str(source_path)
    current_hash = compute_hash(source_path)
    entry: SourceEntry = sources.get(key, {})
    entry["content_hash"] = current_hash
    entry["last_ingested"] = datetime.now(timezone.utc).isoformat()
    if pages_produced is not None:
        entry["pages_produced"] = pages_produced
    sources[key] = entry
    _save_manifest(vault, sources)
    return current_hash


def hash_file(path: Path) -> str:
    """Just compute and return the hash — no manifest I/O."""
    return compute_hash(path)
