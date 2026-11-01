"""What `llm-wiki init` can build: two packs, plus roles that add folders.

A vault starts from a pack:

- standard -- one folder per page type named in Karpathy's LLM-wiki gist:
  references/, entities/, synthesis/, concepts/.
- minimal  -- the gist's single wiki/ folder. Each page's `category:` still
  names its kind (references, entities, synthesis, concepts), so index.md
  can group pages the way the gist's index does.

On the standard pack, roles add the one or two folders a kind of work needs
(a learner gets courses/, a team gets meetings/ and decisions/). People mix
roles, so roles combine rather than being separate packs.

`compose()` turns those choices into the vault's CATEGORIES rows. Nothing here
touches the filesystem; scaffold.py writes the vault.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable

from llm_wiki.layout import Category, validate

DEFAULT_PACK = "standard"


class PresetError(ValueError):
    """The requested choices can't make a valid vault. Carries every problem."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass(frozen=True)
class Folder:
    """One CATEGORIES row a pack or add-on contributes."""

    folder: str
    holds: str
    role: str | None
    template: str  # file stem under presets/templates/


@dataclass(frozen=True)
class Pack:
    name: str
    summary: str
    folders: tuple[Folder, ...]  # filing order; the last row is the catch-all
    kinds: tuple[str, ...] = ()  # single-folder packs: the `category:` values pages use
    takes_roles: bool = True


@dataclass(frozen=True)
class Role:
    name: str
    label: str
    summary: str
    adds: tuple[str, ...]  # add-on names
    staged_writes: bool = False  # suggest WIKI_STAGED_WRITES=true: a human approves agent edits
    history_import: bool = False  # suggest mining Claude Code history after setup


PACKS: dict[str, Pack] = {
    "standard": Pack(
        name="standard",
        summary="one folder per page type in Karpathy's LLM-wiki gist",
        folders=(
            Folder("references", "One page per ingested source; cites the `_inbox/` original", "reference", "reference"),
            Folder("entities", "One page per proper noun: person, tool, organization, product", "entity", "entity"),
            Folder(
                "synthesis",
                "Insights and comparisons that only exist by combining several pages",
                "synthesis",
                "synthesis",
            ),
            Folder(
                "concepts",
                "Ideas, patterns, mental models, how-tos — and anything no row above fits",
                "concept",
                "concept",
            ),
        ),
    ),
    "minimal": Pack(
        name="minimal",
        summary="every page in one wiki/ folder, as in Karpathy's gist",
        folders=(
            Folder(
                "wiki",
                "Every page. Set `category:` to the page's kind instead of the folder: "
                "`references` (one source), `entities` (a proper noun), "
                "`synthesis` (combines pages) or `concepts` (anything else)",
                "concept",
                "page",
            ),
        ),
        kinds=("references", "entities", "synthesis", "concepts"),
        takes_roles=False,
    ),
}

# Folders roles can add. This order is also their filing order: they sit above
# the pack's own rows, because a page that fits a folder you asked for (a
# meeting, a decision, an idea) should land there before the general rows.
ADDONS: dict[str, Folder] = {
    "meetings": Folder(
        "meetings",
        "One page per meeting: who attended, what was decided, follow-ups (`YYYY-MM-DD-topic.md`)",
        None,
        "meeting",
    ),
    "decisions": Folder("decisions", "One page per decision: the options, the choice, and why", None, "decision"),
    "journal": Folder("journal", "Personal logs and reflections, one page per day (`YYYY-MM-DD.md`)", "journal", "journal-entry"),
    "projects": Folder(
        "projects",
        "One overview page per project or product: goal, status, and links to its pages",
        "project",
        "project",
    ),
    "courses": Folder(
        "courses",
        "One hub page per course or book: what it covers, its lectures or chapters, the concepts it built",
        None,
        "course",
    ),
    "questions": Folder(
        "questions",
        "One page per open question you are researching: the current best answer and its evidence",
        None,
        "question",
    ),
    "ideas": Folder("ideas", "Content ideas: the angle, the hook, and the pages to draw on", None, "idea"),
    "outputs": Folder(
        "outputs",
        "One page per thing you made from the wiki (post, video, newsletter, talk): what it was and which pages it used",
        None,
        "output",
    ),
}

ROLES: dict[str, Role] = {
    "learner": Role("learner", "Learner", "courses, books, self-study", ("courses",)),
    "researcher": Role("researcher", "Researcher", "papers and reports, building a thesis over time", ("questions",)),
    "indie-hacker": Role(
        "indie-hacker", "Indie hacker", "building products on your own", ("projects",), history_import=True
    ),
    "creator": Role("creator", "Content creator", "research for posts, videos, newsletters", ("ideas", "outputs")),
    "team": Role(
        "team", "Team", "a shared wiki fed by meetings, chats and docs", ("meetings", "decisions"), staged_writes=True
    ),
    "personal": Role("personal", "Personal", "goals, health, reflections", ("journal",)),
}

# The demo pages under presets/demo/ and the role each one plays. init files
# every page in the folder that holds its role, so the same five pages work in
# any layout.
DEMO_PAGES: dict[str, str] = {
    "karpathy-llm-wiki": "reference",
    "llm-wiki-framework": "entity",
    "why-agents-need-a-constitution": "synthesis",
    "llm-wiki-pattern": "concept",
    "ingest-a-source": "concept",
}

# In a single-folder pack, a page's `category:` names its kind, not its folder.
KIND_OF_ROLE: dict[str, str] = {
    "reference": "references",
    "entity": "entities",
    "synthesis": "synthesis",
    "concept": "concepts",
}

# Page stems already used by every vault. A folder of your own gets a page
# template named after it, so its name must not collide with these.
RESERVED_NAMES = frozenset(
    {"index", "log", "hot", "readme", "agents", "claude", "taxonomy", "trust-ledger", "_insights"}
) | frozenset(DEMO_PAGES)


@dataclass(frozen=True)
class Row:
    """A CATEGORIES row of the vault being built, plus where its template comes from."""

    folder: str
    holds: str
    role: str | None
    template: str  # source stem under presets/templates/
    template_as: str  # stem written to the vault's _meta/templates/
    origin: str  # "pack", "addon:<name>", or "custom"

    @property
    def category(self) -> Category:
        return Category(self.folder, self.holds, self.role)


@dataclass(frozen=True)
class Plan:
    """Everything init needs to write a vault, already validated."""

    pack: Pack
    roles: tuple[str, ...]
    addons: tuple[str, ...]  # add-ons asked for directly, beyond the roles
    custom: tuple[str, ...]  # folders of the user's own
    renames: tuple[tuple[str, str], ...]
    rows: tuple[Row, ...]

    @property
    def categories(self) -> tuple[Category, ...]:
        return tuple(row.category for row in self.rows)

    @property
    def folders(self) -> tuple[str, ...]:
        return tuple(row.folder for row in self.rows)

    def category_value(self, row: Row, role: str | None = None) -> str:
        """The `category:` a page in *row* carries.

        Folder-per-kind packs use the folder. A single-folder pack uses the
        page's kind: *role* when known (demo pages), else the catch-all kind.
        """
        if self.pack.kinds:
            return KIND_OF_ROLE.get(role or "", self.pack.kinds[-1])
        return row.folder

    def suggests_staged_writes(self) -> bool:
        return any(ROLES[name].staged_writes for name in self.roles)

    def suggests_history_import(self) -> bool:
        return any(ROLES[name].history_import for name in self.roles)


def _dedupe(names: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for name in names:
        name = name.strip()
        if name and name not in seen:
            seen.append(name)
    return seen


def _clean(name: str) -> str:
    return name.strip().strip("`").strip().rstrip("/")


def compose(
    pack: str = DEFAULT_PACK,
    roles: Iterable[str] = (),
    addons: Iterable[str] = (),
    folders: Iterable[tuple[str, str]] = (),
    renames: Iterable[tuple[str, str]] = (),
) -> Plan:
    """Validated rows for a vault built from *pack* plus the given choices.

    *folders* are the user's own (name, what it holds) pairs; *renames* are
    (old, new) folder names applied last. Raises PresetError with every
    problem found.
    """
    chosen = PACKS.get(pack)
    if chosen is None:
        raise PresetError([f"unknown pack `{pack}` (choose: {', '.join(PACKS)})"])
    role_names = _dedupe(roles)
    addon_names = _dedupe(addons)
    folders = [(_clean(name), holds.strip()) for name, holds in folders]
    renames = [(_clean(old), _clean(new)) for old, new in renames]
    if not chosen.takes_roles and (role_names or addon_names or folders):
        raise PresetError(
            [f"the {chosen.name} pack is a single folder; roles, add-ons and folders of your own need the standard pack"]
        )

    problems: list[str] = []
    wanted: set[str] = set()
    for name in role_names:
        if name not in ROLES:
            problems.append(f"unknown role `{name}` (choose: {', '.join(ROLES)})")
        else:
            wanted.update(ROLES[name].adds)
    for name in addon_names:
        if name not in ADDONS:
            problems.append(f"unknown add-on `{name}` (choose: {', '.join(ADDONS)})")
        else:
            wanted.add(name)

    rows = [
        Row(addon.folder, addon.holds, addon.role, addon.template, addon.template, f"addon:{name}")
        for name, addon in ADDONS.items()
        if name in wanted
    ]
    for name, holds in folders:
        if not holds:
            problems.append(f"folder `{name}/` needs a description of what it holds")
        rows.append(Row(name, holds, None, "page", name, "custom"))
    rows.extend(Row(f.folder, f.holds, f.role, f.template, f.template, "pack") for f in chosen.folders)

    for old, new in renames:
        at = [index for index, row in enumerate(rows) if row.folder == old]
        if not at:
            problems.append(f"cannot rename `{old}/`: this vault has no such folder")
            continue
        row = rows[at[0]]
        # A folder of your own names its template after itself, so it follows the rename.
        rows[at[0]] = replace(row, folder=new, template_as=new if row.origin == "custom" else row.template_as)

    problems.extend(validate(row.category for row in rows))
    templates_seen: dict[str, str] = {}
    for row in rows:
        if row.origin == "custom" and row.folder in RESERVED_NAMES:
            problems.append(f"`{row.folder}` is already the name of a vault page; pick another folder name")
        owner = templates_seen.get(row.template_as)
        if owner is not None and owner != row.folder:
            problems.append(
                f"folders `{owner}/` and `{row.folder}/` would both use the page template "
                f"`{row.template_as}.md`; rename one of them"
            )
        templates_seen.setdefault(row.template_as, row.folder)
    if problems:
        raise PresetError(_dedupe(problems))

    return Plan(
        pack=chosen,
        roles=tuple(role_names),
        addons=tuple(name for name in addon_names if not any(name in ROLES[r].adds for r in role_names)),
        custom=tuple(row.folder for row in rows if row.origin == "custom"),
        renames=tuple(renames),
        rows=tuple(rows),
    )


def catalog() -> dict[str, Any]:
    """Packs, roles and add-ons as plain data, for `llm-wiki presets --json`."""

    def folder_dict(folder: Folder) -> dict[str, Any]:
        return {"folder": folder.folder, "holds": folder.holds, "role": folder.role}

    return {
        "default_pack": DEFAULT_PACK,
        "packs": [
            {
                "name": pack.name,
                "summary": pack.summary,
                "folders": [folder_dict(folder) for folder in pack.folders],
                "takes_roles": pack.takes_roles,
            }
            for pack in PACKS.values()
        ],
        "roles": [
            {
                "name": role.name,
                "label": role.label,
                "summary": role.summary,
                "adds": [ADDONS[name].folder for name in role.adds],
                "suggests": {"staged_writes": role.staged_writes, "history_import": role.history_import},
            }
            for role in ROLES.values()
        ],
        "addons": [{"name": name, **folder_dict(folder)} for name, folder in ADDONS.items()],
    }
