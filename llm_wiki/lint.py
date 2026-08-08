"""Vault lint checks for wiki structure and metadata hygiene."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SKIP_DIRS = frozenset("_raw _archived _staging _archives .obsidian".split())
REQUIRED_FRONTMATTER = ("title", "category", "tags", "sources", "created", "updated")
# Law 4's eighth field, required of wiki pages only. Law 3 puts wiki pages in
# these folders and nowhere else, so everything outside them -- root files like
# index/log/hot and the constitution, plus _meta/ system data -- is bookkeeping
# rather than knowledge. A lifecycle on those would assert a trust state that
# does not apply: "draft" on AGENTS.md would read as "no human checked this".
CONTENT_DIRS = frozenset("concepts entities skills references synthesis journal projects".split())
RESERVED_PAGE_STEMS = frozenset({"index", "log", "hot", "_insights"})
VALID_LIFECYCLE = ("draft", "reviewed", "verified", "disputed", "archived")

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_FIELD_RE = re.compile(r"^([A-Za-z_][\w-]*):", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")
_MD_LINK_RE = re.compile(r"\[.*?\]\(([^)]+\.md[^)]*)\)")


def _slug(text: str) -> str:
    return text.strip().lower().replace(" ", "-")


def _iter_pages(vault: Path) -> list[Path]:
    return [
        path for path in vault.rglob("*.md")
        if not any(part in SKIP_DIRS for part in path.relative_to(vault).parts)
    ]


def _parse_frontmatter_values(frontmatter: str) -> dict[str, str]:
    values: dict[str, str] = {}
    lines = frontmatter.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or ":" not in line or line.startswith((" ", "\t")):
            i += 1
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        value = raw.strip()
        if value in {">", ">-", "|", "|-"}:
            block: list[str] = []
            i += 1
            while i < len(lines):
                child = lines[i]
                if child.startswith(" ") or child.startswith("\t"):
                    block.append(child.strip())
                    i += 1
                    continue
                break
            values[key] = " ".join(part for part in block if part).strip()
            continue
        values[key] = value.strip("'\"")
        i += 1
    return values


def _parse_page(path: Path, vault: Path) -> dict[str, Any]:
    relative = path.relative_to(vault)
    text = path.read_text(encoding="utf-8", errors="replace")
    front_match = _FRONTMATTER_RE.match(text)
    frontmatter = front_match.group(1) if front_match else ""
    fields = set(_FIELD_RE.findall(frontmatter))
    values = _parse_frontmatter_values(frontmatter)

    links: list[str] = []
    for raw in _WIKILINK_RE.findall(text):
        target = _slug(raw.split("/")[-1])
        if target:
            links.append(target)
    for href in _MD_LINK_RE.findall(text):
        target = _slug(Path(href).stem)
        if target:
            links.append(target)

    return {
        "path": str(relative),
        "slug": _slug(path.stem),
        "is_wiki_page": len(relative.parts) > 1 and relative.parts[0] in CONTENT_DIRS,
        "title": values.get("title", "").strip() or path.stem,
        "summary": values.get("summary", "").strip(),
        "lifecycle": values.get("lifecycle", "").strip(),
        "fields": fields,
        "links": links,
    }


def lint_vault(vault: Path) -> dict[str, Any]:
    pages = [_parse_page(path, vault) for path in _iter_pages(vault)]
    by_slug = {page["slug"]: page for page in pages}
    incoming: dict[str, int] = defaultdict(int)

    broken_links: list[dict[str, str]] = []
    for page in pages:
        for target in page["links"]:
            if target == page["slug"]:
                continue
            if target not in by_slug:
                broken_links.append({"page": page["path"], "target": target})
                continue
            incoming[target] += 1

    missing_frontmatter = []
    for page in pages:
        required = REQUIRED_FRONTMATTER + (("lifecycle",) if page["is_wiki_page"] else ())
        missing = [field for field in required if field not in page["fields"]]
        if missing:
            missing_frontmatter.append({"page": page["path"], "missing": missing})

    title_index: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        title_index[page["title"].strip().lower()].append(page["path"])
    duplicate_titles = [
        {"title": title, "pages": paths}
        for title, paths in title_index.items()
        if title and len(paths) > 1
    ]
    duplicate_titles.sort(key=lambda item: (item["title"], item["pages"]))

    missing_summaries = [
        page["path"]
        for page in pages
        if "summary" not in page["fields"] or not page["summary"]
    ]

    # Absence is not flagged here -- missing_frontmatter owns that, and only for
    # wiki pages (see CONTENT_DIRS). This check only rejects values that are not
    # states in the machine at all, wherever they appear.
    invalid_lifecycle = [
        {"page": page["path"], "value": page["lifecycle"]}
        for page in pages
        if page["lifecycle"] and page["lifecycle"] not in VALID_LIFECYCLE
    ]

    orphan_pages = []
    for page in pages:
        if page["slug"] in RESERVED_PAGE_STEMS:
            continue
        outgoing = sum(1 for target in page["links"] if target in by_slug and target != page["slug"])
        if outgoing == 0 and incoming.get(page["slug"], 0) == 0:
            orphan_pages.append(page["path"])

    findings = {
        "broken_links": broken_links,
        "missing_frontmatter": missing_frontmatter,
        "invalid_lifecycle": invalid_lifecycle,
        "duplicate_titles": duplicate_titles,
        "missing_summaries": sorted(missing_summaries),
        "orphan_pages": sorted(orphan_pages),
    }
    counts = {name: len(items) for name, items in findings.items()}

    if counts["broken_links"] or counts["missing_frontmatter"] or counts["invalid_lifecycle"]:
        status = "fail"
    elif any(counts[name] for name in ("duplicate_titles", "missing_summaries", "orphan_pages")):
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "stats": {
            "pages": len(pages),
            "link_count": sum(len(page["links"]) for page in pages),
            "findings": counts,
        },
        "findings": findings,
    }
