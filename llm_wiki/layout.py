"""The vault's page folders, read from the CATEGORIES table in its AGENTS.md.

Every vault declares where wiki pages may live (law 3) in one markdown table:

    ## CATEGORIES

    | Folder | Holds | Role |
    |---|---|---|
    | `references/` | One page per ingested source | reference |
    | `concepts/` | Ideas -- and anything no row above fits | concept |

Rows are in filing order: an agent files a page in the first row whose *Holds*
fits it, and the last row takes everything else. *Role* names the built-in
part a folder plays, so a skill can ask "where do synthesis pages go here?"
without knowing the vault's folder names. A role no row claims falls to the
last row.

lint, doctor, and init all read the table through this module, so they agree
on one answer. A vault whose AGENTS.md has no CATEGORIES table predates it and
keeps the original seven-folder layout, unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# The built-in parts a folder can play. Skills route by role, never by folder
# name: "file this paper in the reference folder", "write the digest to the
# journal folder". `procedure` is only claimed by the original layout's skills/.
ROLES = ("concept", "entity", "reference", "synthesis", "journal", "project", "procedure")

_HEADING_RE = re.compile(r"^##\s+categories\b", re.IGNORECASE)
_SECTION_END_RE = re.compile(r"^#{1,2}\s")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_FOLDER_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_NO_ROLE = frozenset({"", "-", "—", "–"})  # empty, hyphen, em dash, en dash


class LayoutError(ValueError):
    """The CATEGORIES table exists but cannot be used. Carries every problem."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass(frozen=True)
class Category:
    folder: str
    holds: str
    role: str | None = None


@dataclass(frozen=True)
class Layout:
    categories: tuple[Category, ...]
    source: str  # "AGENTS.md" when read from the table, "default" otherwise

    @property
    def folders(self) -> frozenset[str]:
        return frozenset(category.folder for category in self.categories)

    @property
    def catch_all(self) -> Category:
        return self.categories[-1]

    def folder_for(self, role: str) -> str:
        """The folder that plays *role*, or the catch-all when no row claims it."""
        if role not in ROLES:
            raise KeyError(f"unknown role: {role}")
        for category in self.categories:
            if category.role == role:
                return category.folder
        return self.catch_all.folder

    def roles(self) -> dict[str, str]:
        return {role: self.folder_for(role) for role in ROLES}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "categories": [
                {"folder": c.folder, "holds": c.holds, "role": c.role}
                for c in self.categories
            ],
            "catch_all": self.catch_all.folder,
            "roles": self.roles(),
        }


# The layout every vault had before the CATEGORIES table existed. Vaults
# without a table keep it, so their lint and doctor results never change.
LEGACY_LAYOUT = Layout(
    categories=(
        Category("journal", "Dated session logs and observations (`YYYY-MM-DD.md`)", "journal"),
        Category(
            "projects",
            "One page per project: `projects/<name>.md`; nest to `projects/<name>/<name>.md` "
            "plus scoped subfolders only past ~5 related pages",
            "project",
        ),
        Category("references", "One page per ingested source; cites the `_inbox/` original", "reference"),
        Category("entities", "One page per proper noun: tool, person, org, product", "entity"),
        Category("skills", "One page per reusable procedure (knowledge, not agent skills)", "procedure"),
        Category("synthesis", "Insights that only exist by combining multiple pages", "synthesis"),
        Category("concepts", "Standalone ideas, patterns, mental models, and anything no row above fits", "concept"),
    ),
    source="default",
)


def validate(categories: Iterable[Category]) -> list[str]:
    """Problems that make a set of categories unusable. Empty means valid."""
    problems: list[str] = []
    seen_folders: set[str] = set()
    role_owner: dict[str, str] = {}
    count = 0
    for category in categories:
        count += 1
        folder = category.folder
        if not folder:
            problems.append("a row has no folder")
            continue
        if "/" in folder or "\\" in folder:
            problems.append(f"folder `{folder}` must be a single top-level folder")
        elif folder[0] in "_.":
            problems.append(
                f"folder `{folder}/` starts with `{folder[0]}`, which marks system folders; "
                "pick a name without it"
            )
        elif not _FOLDER_RE.match(folder):
            problems.append(f"folder `{folder}` must use only lowercase letters, digits and hyphens")
        if folder in seen_folders:
            problems.append(f"folder `{folder}/` appears more than once")
        seen_folders.add(folder)

        role = category.role
        if role is None:
            continue
        if role not in ROLES:
            problems.append(f"folder `{folder}/` has unknown role `{role}` (known: {', '.join(ROLES)})")
        elif role in role_owner:
            problems.append(f"role `{role}` is claimed by both `{role_owner[role]}/` and `{folder}/`")
        else:
            role_owner[role] = folder
    if count == 0:
        problems.append("the CATEGORIES table has no rows")
    return problems


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [cell.strip().replace("\\|", "|") for cell in _CELL_SPLIT_RE.split(body)]


def _clean_folder(cell: str) -> str:
    return cell.strip().strip("`").strip().rstrip("/")


def _clean_role(cell: str) -> str | None:
    value = cell.strip().strip("`").strip().lower()
    return None if value in _NO_ROLE else value


def find_table(lines: list[str]) -> tuple[int, int] | None:
    """Line span ``(start, end)`` of the CATEGORIES table, end exclusive.

    Returns None when there is no CATEGORIES heading (outside code fences).
    Raises LayoutError when the heading appears twice or its section has no
    table before the next heading.
    """
    headings: list[int] = []
    in_fence = False
    for index, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and _HEADING_RE.match(line):
            headings.append(index)
    if not headings:
        return None
    if len(headings) > 1:
        raise LayoutError(["AGENTS.md has more than one CATEGORIES section"])

    in_fence = False
    index = headings[0] + 1
    while index < len(lines):
        line = lines[index]
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            if _SECTION_END_RE.match(line):
                break
            if line.strip().startswith("|"):
                start = index
                while index < len(lines) and lines[index].strip().startswith("|"):
                    index += 1
                return start, index
        index += 1
    raise LayoutError(["the CATEGORIES section has no table"])


def parse_categories(text: str) -> tuple[Category, ...] | None:
    """Categories from an AGENTS.md text; None when it has no CATEGORIES table."""
    lines = text.splitlines()
    span = find_table(lines)
    if span is None:
        return None
    rows = lines[span[0]:span[1]]
    if len(rows) < 2 or not all(_SEPARATOR_RE.match(cell) for cell in _cells(rows[1])):
        raise LayoutError(["the CATEGORIES table needs a header row followed by a |---| separator row"])

    header = [cell.strip("*_` ").lower() for cell in _cells(rows[0])]
    missing = [name for name in ("folder", "holds", "role") if name not in header]
    if missing:
        raise LayoutError(
            [f"the CATEGORIES table has no {name.title()} column" for name in missing]
        )
    at = {name: header.index(name) for name in ("folder", "holds", "role")}

    problems: list[str] = []
    categories: list[Category] = []
    for number, row in enumerate(rows[2:], start=1):
        cells = _cells(row)
        if len(cells) != len(header):
            problems.append(
                f"row {number} has {len(cells)} cells but the header has {len(header)} "
                "(write a `|` inside a cell as `\\|`)"
            )
            continue
        categories.append(
            Category(
                folder=_clean_folder(cells[at["folder"]]),
                holds=cells[at["holds"]],
                role=_clean_role(cells[at["role"]]),
            )
        )
    # With every row already rejected for its cell count, "no rows" would mislead.
    if categories or not problems:
        problems.extend(validate(categories))
    if problems:
        raise LayoutError(problems)
    return tuple(categories)


def load_layout(vault: Path) -> Layout:
    """The vault's layout. Raises LayoutError when its CATEGORIES table is broken."""
    agents = vault / "AGENTS.md"
    if not agents.is_file():
        return LEGACY_LAYOUT
    try:
        text = agents.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise LayoutError([f"cannot read AGENTS.md: {exc}"]) from exc
    categories = parse_categories(text)
    if categories is None:
        return LEGACY_LAYOUT
    return Layout(categories=categories, source="AGENTS.md")


def render_table(categories: Iterable[Category]) -> str:
    """The CATEGORIES table as markdown, in the exact shape parse_categories reads."""
    lines = ["| Folder | Holds | Role |", "|---|---|---|"]
    for category in categories:
        holds = category.holds.replace("|", "\\|")
        lines.append(f"| `{category.folder}/` | {holds} | {category.role or ''} |")
    return "\n".join(lines)
