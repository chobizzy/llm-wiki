"""Batch planner for parallel wiki-ingest subagent dispatch.

When ingesting a large folder of docs, this module splits the source list into
batches and emits a dispatch plan the skill uses to spawn parallel Claude
subagents — each handling one batch independently, then merging results.

The agent calls `llm-wiki batch-plan <vault> <source-dir> [options]`
and gets back a JSON plan:

{
  "batches": [
    {
      "id": 0,
      "files": ["path/to/a.md", "path/to/b.pdf"],
      "total_bytes": 45000,
      "kinds": {"markdown": 1, "pdf": 1}
    },
    ...
  ],
  "stats": {
    "total_files": N,
    "total_bytes": N,
    "batch_count": N,
    "skipped_unchanged": N,
    "skipped_binary": N
  },
  "merge_hint": "Run /wiki-ingest on each batch in parallel, then run /cross-linker once all batches are done."
}

The skill dispatches each batch as a parallel subagent call, then runs
cross-linker once all agents report completion.
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------

# Ingestible text/doc extensions
TEXT_EXTENSIONS = frozenset(
    ".md .mdx .txt .rst .html .htm .csv .tsv .json .jsonl .yaml .yml .xml".split()
)
PDF_EXTENSIONS = frozenset(".pdf".split())
IMAGE_EXTENSIONS = frozenset(".png .jpg .jpeg .webp .gif .bmp .tiff .svg".split())
OFFICE_EXTENSIONS = frozenset(".docx .xlsx .pptx .odt .ods .odp".split())
CODE_EXTENSIONS = frozenset(
    ".py .ts .js .jsx .tsx .go .rs .java .kt .rb .c .cpp .h .hpp .swift .sh".split()
)

# Binary / generated — skip entirely
SKIP_EXTENSIONS = frozenset(
    ".pyc .pyo .pyd .so .dylib .dll .exe .class .jar .war .egg "
    ".zip .tar .gz .bz2 .whl .lock .mp4 .mov .mp3 .wav .ttf .woff .eot".split()
)

SKIP_DIRS = frozenset(
    "node_modules .git __pycache__ .pytest_cache dist build target "
    ".venv venv env .mypy_cache .ruff_cache coverage .tox .obsidian "
    "_raw _archived _staging _archives".split()
)


def _classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in OFFICE_EXTENSIONS:
        return "office"
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in SKIP_EXTENSIONS:
        return "skip"
    # Guess via mime
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("text/"):
        return "text"
    return "skip"


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------

def discover_sources(
    source_dir: Path,
    *,
    vault: Path | None = None,
    include_code: bool = False,
) -> tuple[list[dict], int]:
    """Walk source_dir and return (ingestible file dicts, skipped binary count).

    Each dict: {path, kind, size_bytes}. Code files are excluded by default
    because wiki-ingest Step 1c handles them via ast-extract separately, and
    are not counted as skipped binaries.
    """
    files = []
    skipped_binary = 0
    for dirpath, dirnames, filenames in os.walk(source_dir):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            kind = _classify(p)
            if kind == "skip":
                skipped_binary += 1
                continue
            if kind == "code" and not include_code:
                continue
            files.append({"path": str(p), "kind": kind, "size_bytes": _file_size(p)})
    return files, skipped_binary


# ---------------------------------------------------------------------------
# Manifest filtering (skip unchanged sources)
# ---------------------------------------------------------------------------

def _filter_unchanged(
    files: list[dict],
    vault: Path,
) -> tuple[list[dict], int]:
    """Remove files whose hash matches the manifest. Returns (to_ingest, skipped_count)."""
    try:
        from llm_wiki.cache import ManifestError, check_sources, compute_hash
        paths = [Path(f["path"]) for f in files]
        result = check_sources(vault, paths)
        unchanged_set = set(result["unchanged"])
        to_ingest = [f for f in files if f["path"] not in unchanged_set]
        return to_ingest, len(unchanged_set)
    except ManifestError:
        # A damaged ledger must stop the plan. Falling through to "ingest
        # everything" here would look like a normal first run of a big folder.
        raise
    except Exception:
        return files, 0


# ---------------------------------------------------------------------------
# Batch splitting
# ---------------------------------------------------------------------------

def _make_batches(
    files: list[dict],
    *,
    max_batch_bytes: int,
    max_batch_files: int,
) -> list[list[dict]]:
    """Split files into batches respecting size and file-count limits."""
    batches: list[list[dict]] = []
    current: list[dict] = []
    current_bytes = 0

    for f in files:
        sz = f["size_bytes"]
        if current and (
            current_bytes + sz > max_batch_bytes
            or len(current) >= max_batch_files
        ):
            batches.append(current)
            current = []
            current_bytes = 0
        current.append(f)
        current_bytes += sz

    if current:
        batches.append(current)
    return batches


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def plan_batches(
    source_dir: Path,
    vault: Path,
    *,
    max_batch_mb: float = 2.0,
    max_batch_files: int = 20,
    skip_unchanged: bool = True,
    include_code: bool = False,
) -> dict[str, Any]:
    """Discover sources, filter unchanged, and split into batches."""
    all_files, skipped_binary = discover_sources(
        source_dir, vault=vault, include_code=include_code
    )

    skipped_unchanged = 0

    to_ingest = all_files
    if skip_unchanged and vault.is_dir():
        to_ingest, skipped_unchanged = _filter_unchanged(all_files, vault)

    max_batch_bytes = int(max_batch_mb * 1024 * 1024)
    batches_raw = _make_batches(
        to_ingest,
        max_batch_bytes=max_batch_bytes,
        max_batch_files=max_batch_files,
    )

    total_bytes = sum(f["size_bytes"] for f in to_ingest)

    batches_out = []
    for i, batch in enumerate(batches_raw):
        kinds: dict[str, int] = {}
        for f in batch:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
        batches_out.append({
            "id": i,
            "files": [f["path"] for f in batch],
            "total_bytes": sum(f["size_bytes"] for f in batch),
            "kinds": kinds,
        })

    merge_hint = (
        "Dispatch each batch as a parallel subagent with /wiki-ingest on its file list. "
        "Once all batches complete, run /cross-linker to wire up cross-references."
    )

    return {
        "batches": batches_out,
        "stats": {
            "total_files": len(all_files),
            "to_ingest": len(to_ingest),
            "total_bytes": total_bytes,
            "batch_count": len(batches_out),
            "skipped_unchanged": skipped_unchanged,
            "skipped_binary": skipped_binary,
        },
        "merge_hint": merge_hint,
    }
