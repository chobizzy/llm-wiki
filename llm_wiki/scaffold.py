"""Write a new vault: `llm-wiki init`, its preview, and its setup interview.

The vault is assembled from presets/ in the repo checkout:

    presets/base/       files every vault gets (AGENTS.md, README.md, ...)
    presets/templates/  page templates, one per kind of folder
    presets/demo/       demo pages, filed by role into whatever folders exist
    presets/backup/     the optional GitHub backup hook

It is built in a temporary folder next to the target and moved into place
only when complete, so a failure never leaves a half-written vault behind.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from llm_wiki.layout import Layout, render_table
from llm_wiki.presets import ADDONS, DEFAULT_PACK, DEMO_PAGES, PACKS, ROLES, Plan, PresetError, compose

TABLE_MARKER = "<!-- llm-wiki init writes the CATEGORIES table here -->"
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

Ask = Callable[[str], str]
Say = Callable[[str], None]


class ScaffoldError(RuntimeError):
    """The vault can't be written where it was asked for."""


def presets_dir() -> Path:
    """The presets folder: next to the package in a checkout, or bundled data."""
    package = Path(__file__).resolve().parent
    for candidate in (package.parent / "presets", package / "_data" / "presets"):
        if (candidate / "base").is_dir():
            return candidate
    raise FileNotFoundError(
        "Could not locate the presets folder. Expected it next to the llm_wiki "
        "package (repo checkout) or bundled as package data."
    )


def check_target(target: Path) -> None:
    """Refuse anything but a new or empty folder: init never overwrites."""
    if target.exists():
        if not target.is_dir():
            raise ScaffoldError(f"{target} exists and is not a folder")
        if any(target.iterdir()):
            raise ScaffoldError(f"{target} is not empty; init only writes into a new or empty folder")


# ── Writing ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DemoPage:
    slug: str
    folder: str
    category: str
    summary: str
    tags: tuple[str, ...]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")  # universal newlines: CRLF arrives as LF


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _copy_tree(source: Path, dest: Path) -> list[Path]:
    """Copy every file under *source* into *dest* with LF line endings."""
    written: list[Path] = []
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        target = dest / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        written.append(target)
    return written


def _fill(path: Path, tokens: dict[str, str]) -> None:
    text = _read(path)
    for token, value in tokens.items():
        text = text.replace(token, value)
    _write(path, text)


def _frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(text)
    values: dict[str, str] = {}
    if match:
        for line in match.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep and not line.startswith((" ", "\t")):
                values[key.strip()] = value.strip()
    return values


def _tags(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return ()
    return tuple(tag.strip().strip("'\"") for tag in value[1:-1].split(",") if tag.strip())


def _title(key: str) -> str:
    words = key.replace("-", " ")
    return words[:1].upper() + words[1:]


def _staging_dir(target: Path) -> Path:
    for attempt in range(100):
        candidate = target.parent / f".{target.name}.llm-wiki-init-{os.getpid()}-{attempt}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise ScaffoldError(f"could not create a temporary folder in {target.parent}")


def create_vault(
    target: Path,
    plan: Plan,
    *,
    demo: bool = True,
    backup_hook: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Write a vault for *plan* at *target*, a new or empty folder."""
    target = Path(target).expanduser().absolute()
    check_target(target)
    root = presets_dir()
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = _staging_dir(target)
    try:
        summary = _build(staging, target, root, plan, demo, backup_hook, now)
        if target.exists():
            target.rmdir()  # empty: check_target said so
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def _build(
    staging: Path,
    target: Path,
    root: Path,
    plan: Plan,
    demo: bool,
    backup_hook: bool,
    now: datetime,
) -> dict[str, Any]:
    _copy_tree(root / "base", staging)

    agents = staging / "AGENTS.md"
    text = _read(agents)
    if TABLE_MARKER not in text:
        raise ScaffoldError("presets/base/AGENTS.md has lost its CATEGORIES table marker")
    _write(agents, text.replace(TABLE_MARKER, render_table(plan.categories)))

    for row in plan.rows:
        (staging / row.folder).mkdir(parents=True, exist_ok=True)
        template = _read(root / "templates" / f"{row.template}.md")
        template = template.replace("__CATEGORY__", plan.category_value(row)).replace("__HOLDS__", row.holds)
        _write(staging / "_meta" / "templates" / f"{row.template_as}.md", template)

    pages: list[DemoPage] = []
    if demo:
        layout = Layout(plan.categories, source="AGENTS.md")
        rows = {row.folder: row for row in plan.rows}
        for slug, role in DEMO_PAGES.items():
            folder = layout.folder_for(role)
            category = plan.category_value(rows[folder], role)
            page = _read(root / "demo" / f"{slug}.md").replace("__CATEGORY__", category)
            _write(staging / folder / f"{slug}.md", page)
            meta = _frontmatter(page)
            pages.append(DemoPage(slug, folder, category, meta.get("summary", ""), _tags(meta.get("tags", ""))))

    for row in plan.rows:  # git doesn't keep empty folders
        folder = staging / row.folder
        if not any(folder.iterdir()):
            (folder / ".gitkeep").write_bytes(b"")

    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")  # true UTC (law 11)
    date = now.strftime("%Y-%m-%d")
    _fill(
        staging / "index.md",
        {"__DATE__": date, "__TIMESTAMP__": stamp, "__SECTIONS__": _index_sections(plan, pages)},
    )
    _fill(staging / "log.md", {"__DATE__": date, "__ENTRIES__": _log_entries(plan, target, pages, stamp, demo)})
    recent, threads = _hot_lines(plan, pages, stamp)
    _fill(staging / "hot.md", {"__DATE__": date, "__RECENT__": recent, "__THREADS__": threads})

    if backup_hook:
        for path in _copy_tree(root / "backup", staging):
            if path.parent.name == "hooks":
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    return {
        "path": str(target),
        "pack": plan.pack.name,
        "roles": list(plan.roles),
        "folders": list(plan.folders),
        "templates": [row.template_as for row in plan.rows],
        "demo_pages": [f"{page.folder}/{page.slug}.md" for page in pages],
        "backup_hook": backup_hook,
    }


def _index_entry(page: DemoPage) -> str:
    tags = " ".join(f"#{tag}" for tag in page.tags)
    return f"- [[{page.slug}]] — {page.summary}" + (f" ( {tags})" if tags else "")


def _index_sections(plan: Plan, pages: list[DemoPage]) -> str:
    # A single-folder pack groups by each page's kind, the way the gist's index does.
    keys = list(plan.pack.kinds) if plan.pack.kinds else list(plan.folders)
    blocks: list[str] = []
    for key in keys:
        entries = [_index_entry(page) for page in pages if page.category == key]
        blocks.append("\n\n".join([f"## {_title(key)}", "\n".join(entries)]) if entries else f"## {_title(key)}")
    if not pages:
        blocks[0] += '\n\n*No pages yet. Drop a source in `_inbox/` and say "ingest my inbox".*'
    blocks.append(
        "## Meta\n\n"
        "- [[README]] — how this vault works: feeding it, asking it, checking it, changing its folders ( #meta)"
    )
    return "\n\n".join(blocks)


def _log_entries(plan: Plan, target: Path, pages: list[DemoPage], stamp: str, demo: bool) -> str:
    fields = [f'vault_path="{target}"', f"pack={plan.pack.name}"]
    if plan.roles:
        fields.append("roles=" + ",".join(plan.roles))
    if plan.addons:
        fields.append("added=" + ",".join(plan.addons))
    if plan.custom:
        fields.append("custom=" + ",".join(plan.custom))
    if plan.renames:
        fields.append("renamed=" + ",".join(f"{old}>{new}" for old, new in plan.renames))
    fields.append("categories=" + ",".join(plan.folders))
    fields.append("demo=" + ("yes" if demo else "no"))
    lines = [f"- [{stamp}] INIT agent=llm-wiki " + " ".join(fields)]
    if pages:
        lines.append(
            f'- [{stamp}] SEED agent=llm-wiki pages_created={len(pages)} '
            'notes="demo pages — replace them with your own knowledge"'
        )
    return "\n".join(lines)


def _hot_lines(plan: Plan, pages: list[DemoPage], stamp: str) -> tuple[str, str]:
    folders = ", ".join(f"{folder}/" for folder in plan.folders)
    recent = f"- [{stamp}] INIT — vault created from the {plan.pack.name} pack ({folders})"
    if plan.roles:
        recent += " for: " + ", ".join(ROLES[name].label for name in plan.roles)
    recent += "; demo pages included." if pages else "."
    threads = [
        '- Ingest your first source: drop it in `_inbox/` and say "ingest my inbox".',
        "- Read [[README]] for how the vault works and how to change its folders; "
        "[[AGENTS]] holds the laws every agent follows.",
    ]
    if pages:
        threads.append("- Replace the demo pages (start with [[llm-wiki-pattern]]) as real knowledge accumulates.")
    if plan.suggests_history_import():
        threads.append('- Say "process my Claude history" to mine past Claude Code sessions into the wiki.')
    return recent, "\n".join(threads)


# ── Previewing ───────────────────────────────────────────────────────────────
def _shorten(text: str, limit: int = 64) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:—-") + "…"


def render_preview(target: Path | None, plan: Plan, *, demo: bool = True, backup_hook: bool = False) -> str:
    """The folder tree and CATEGORIES table init would write, without writing."""
    name = (Path(target).name if target else "my-wiki") + "/"
    templates = ", ".join(row.template_as for row in plan.rows)
    meta = f"taxonomy.md, templates/ ({templates})" + (", hooks/post-commit" if backup_hook else "")
    items = [
        ("AGENTS.md", "the laws, and the CATEGORIES table below"),
        ("CLAUDE.md", "imports AGENTS.md for Claude Code"),
        ("README.md", "how this vault works"),
        ("index.md, log.md, hot.md, .manifest.json", ""),
        ("_inbox/", "drop sources here; agents never edit them"),
        ("_meta/", meta),
    ]
    items.extend((f"{row.folder}/", _shorten(row.holds)) for row in plan.rows)
    width = max(len(label) for label, note in items if note) + 2
    lines = [name]
    for index, (label, note) in enumerate(items):
        branch = "└── " if index == len(items) - 1 else "├── "
        lines.append(f"{branch}{label:<{width}}{note}".rstrip())
    if demo:
        lines.append(f"\n{len(DEMO_PAGES)} demo pages are filed by role into these folders.")
    else:
        lines.append("\nNo demo pages.")
    lines.append("\nCATEGORIES table for AGENTS.md (filing order; the last row takes everything else):\n")
    lines.append(render_table(plan.categories))
    return "\n".join(lines)


# ── The setup interview ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class Choices:
    plan: Plan
    demo: bool
    backup_hook: bool


def _pick_one(ask: Ask, say: Say, prompt: str, names: list[str], default: str) -> str:
    while True:
        answer = ask(prompt).strip().lower()
        if not answer:
            return default
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            return names[int(answer) - 1]
        if answer in names:
            return answer
        say(f"  Pick a number from 1 to {len(names)}.")


def _pick_many(ask: Ask, say: Say, prompt: str, names: list[str]) -> list[str]:
    while True:
        answer = ask(prompt).strip().lower()
        if not answer:
            return []
        picked: list[str] = []
        unknown: list[str] = []
        for token in re.split(r"[,\s]+", answer):
            if not token:
                continue
            if token.isdigit() and 1 <= int(token) <= len(names):
                name = names[int(token) - 1]
            elif token in names:
                name = token
            else:
                unknown.append(token)
                continue
            if name not in picked:
                picked.append(name)
        if not unknown:
            return picked
        say(f"  Not a choice: {', '.join(unknown)}. Use numbers from 1 to {len(names)}, separated by commas.")


def _yes_no(ask: Ask, prompt: str, default: bool) -> bool:
    while True:
        answer = ask(prompt).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def _accepts(say: Say, attempt: Callable[[], Any]) -> bool:
    try:
        attempt()
    except PresetError as exc:
        for problem in exc.problems:
            say(f"  {problem}")
        return False
    return True


def interview(ask: Ask | None = None, say: Say | None = None, target: Path | None = None) -> Choices | None:
    """Ask which pack, roles, and extras to use. None when the user cancels."""
    ask = ask or input  # looked up per call, so tests can patch builtins.input
    say = say or print
    try:
        return _interview(ask, say, target)
    except (EOFError, KeyboardInterrupt):
        say("")
        return None


def _interview(ask: Ask, say: Say, target: Path | None) -> Choices | None:
    packs = list(PACKS.values())
    say("Which pack?")
    for number, pack in enumerate(packs, 1):
        folders = " ".join(f"{folder.folder}/" for folder in pack.folders)
        default = " (default)" if pack.name == DEFAULT_PACK else ""
        say(f"  {number}) {pack.name:<9} {folders} — {pack.summary}{default}")
    pack = _pick_one(ask, say, f"Pack [Enter for {DEFAULT_PACK}]: ", [p.name for p in packs], DEFAULT_PACK)

    roles: list[str] = []
    folders: list[tuple[str, str]] = []
    renames: list[tuple[str, str]] = []
    if PACKS[pack].takes_roles:
        say("")
        say("What will you use it for? Each role adds a folder or two; pick any.")
        catalog = list(ROLES.values())
        for number, role in enumerate(catalog, 1):
            adds = " ".join(f"{ADDONS[name].folder}/" for name in role.adds)
            say(f"  {number}) {role.label:<16}+ {adds:<22} {role.summary}")
        roles = _pick_many(ask, say, "Roles, e.g. 1,4 [Enter for none]: ", [role.name for role in catalog])
        say("")
        while True:
            answer = ask("Add a folder of your own as name=what it holds [Enter to skip]: ").strip()
            if not answer:
                break
            name, sep, holds = answer.partition("=")
            if not sep:
                say("  Write it as name=what it holds, e.g. recipes=Cooking recipes: ingredients and steps")
            elif _accepts(say, lambda: compose(pack, roles, (), folders + [(name, holds)], renames)):
                folders.append((name, holds))

    while True:
        answer = ask("Rename a folder as old=new [Enter to skip]: ").strip()
        if not answer:
            break
        old, sep, new = answer.partition("=")
        if not sep:
            say("  Write it as old=new, e.g. concepts=notes")
        elif _accepts(say, lambda: compose(pack, roles, (), folders, renames + [(old, new)])):
            renames.append((old, new))

    say("")
    demo = _yes_no(ask, "Include demo pages that show the conventions? [Y/n] ", True)
    backup = _yes_no(ask, "Push every commit to a GitHub remote with a backup hook? [y/N] ", False)
    plan = compose(pack, roles, (), folders, renames)
    say("")
    say(render_preview(target, plan, demo=demo, backup_hook=backup))
    say("")
    if not _yes_no(ask, "Create this vault? [Y/n] ", True):
        return None
    return Choices(plan=plan, demo=demo, backup_hook=backup)


# ── After writing ────────────────────────────────────────────────────────────
def next_steps(summary: dict[str, Any], plan: Plan, *, from_setup: bool = False) -> str:
    path = summary["path"]
    quoted = f'"{path}"'
    described = f"{plan.pack.name} pack"
    if plan.roles:
        described += " + " + ", ".join(ROLES[name].label for name in plan.roles)
    lines = [
        f"✅  Vault created at {path}",
        f"    {described} · folders: {', '.join(f'{folder}/' for folder in plan.folders)}"
        f" · demo pages: {len(summary['demo_pages'])}",
        "",
        "Next:",
    ]
    steps = [f'cd {quoted} && git init && git add -A && git commit -m "init: vault from the llm-wiki {plan.pack.name} pack"']
    if not from_setup:
        steps.append(f"llm-wiki setup --vault {quoted}   (links the skills into your agents and points them here)")
    steps.append("Open the folder as a vault in Obsidian.")
    steps.append('Drop a source in _inbox/ and tell your agent: "ingest my inbox".')
    lines.extend(f"  {number}. {step}" for number, step in enumerate(steps, 1))

    extras = []
    if summary["backup_hook"]:
        extras.append(
            "Backup: add a private remote, then turn the hook on: "
            "git remote add origin <url> && git config core.hooksPath _meta/hooks"
        )
    if plan.suggests_staged_writes() and not from_setup:
        extras.append(
            'Team vault: set WIKI_STAGED_WRITES="true" in ~/.llm-wiki/config so a human approves agent edits.'
        )
    if plan.suggests_history_import():
        extras.append('Say "process my Claude history" to mine your past Claude Code sessions into the wiki.')
    if extras:
        lines.append("")
        lines.extend(f"  • {extra}" for extra in extras)
    return "\n".join(lines)
