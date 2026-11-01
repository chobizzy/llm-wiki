"""llm-wiki CLI.

Helper commands for the LLM-Wiki skills (graph analysis, ingest caching, batch
planning, AST extraction, linting) plus the installer that links the
``skills/`` folder at the repo root into every supported AI agent's skills
directory and writes ``~/.llm-wiki/config`` so the skills resolve the vault
from any project.

Skills are linked from the repo checkout — never from site-packages — so
uninstalling or upgrading the Python package cannot break installed skills.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from llm_wiki import __version__

HOME = Path.home()
GLOBAL_CONFIG_DIR = HOME / ".llm-wiki"
GLOBAL_CONFIG = GLOBAL_CONFIG_DIR / "config"


# ── Data resolution ──────────────────────────────────────────────────────────
def _pkg_dir() -> Path:
    return Path(__file__).resolve().parent


def skills_dir() -> Path:
    """Return the directory holding the skill folders.

    Editable install / source checkout: ``<repo>/skills`` next to the package.
    Built wheel: ``<pkg>/_data/skills``.
    """
    for cand in (_pkg_dir().parent / "skills", _pkg_dir() / "_data" / "skills"):
        if cand.is_dir():
            return cand
    raise FileNotFoundError(
        "Could not locate the skills folder. Expected it next to the llm_wiki "
        "package (repo checkout) or bundled as package data."
    )


def list_skills() -> list[str]:
    return sorted(p.name for p in skills_dir().iterdir() if p.is_dir())


# ── Skill installation ───────────────────────────────────────────────────────
def install_skills(
    target_dir: Path,
    label: str,
    *,
    subset: tuple[str, ...] | None = None,
    mode: str = "symlink",
    quiet: bool = False,
) -> int:
    """Install skills into *target_dir*. Returns the count installed."""
    src_root = skills_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    installed = 0
    for skill in sorted(p for p in src_root.iterdir() if p.is_dir()):
        name = skill.name
        if subset is not None and name not in subset:
            continue
        link_path = target_dir / name

        if link_path.is_symlink() or link_path.is_file():
            link_path.unlink()
        elif link_path.is_dir():
            # A real directory we previously copied here is safe to replace;
            # anything else is the user's and we leave it alone.
            if (link_path / "SKILL.md").exists():
                shutil.rmtree(link_path)
            else:
                print(f"   ⚠️  {link_path} is not a managed skill, skipping")
                continue

        if mode == "symlink":
            try:
                link_path.symlink_to(skill, target_is_directory=True)
            except OSError:
                # Symlink creation may require Developer Mode on Windows.
                shutil.copytree(skill, link_path)
        else:  # copy
            shutil.copytree(skill, link_path)

        if not (link_path / "SKILL.md").exists():
            raise RuntimeError(f"broken skill install: {link_path} -> {skill}")
        installed += 1

    if not quiet:
        print(f"✅  Installed {installed} skills → {label}")
    return installed


# Agents whose skills directory lives under $HOME: (path-under-home, label,
# subset). Only agents actually present on this machine are provisioned.
GLOBAL_AGENT_DIRS: list[tuple[str, str, tuple[str, ...] | None]] = [
    (".claude/skills", "~/.claude/skills/ (Claude Code)", None),
    (".gemini/skills", "~/.gemini/skills/ (Gemini CLI)", None),
    (".gemini/antigravity/skills", "~/.gemini/antigravity/skills/ (Antigravity, legacy)", None),
    (".codex/skills", "~/.codex/skills/ (Codex)", None),
    (".hermes/skills", "~/.hermes/skills/ (Hermes default)", None),
    (".openclaw/skills", "~/.openclaw/skills/ (OpenClaw)", None),
    (".copilot/skills", "~/.copilot/skills/ (GitHub Copilot CLI)", None),
    (".trae/skills", "~/.trae/skills/ (Trae)", None),
    (".trae-cn/skills", "~/.trae-cn/skills/ (Trae CN)", None),
    (".kiro/skills", "~/.kiro/skills/ (Kiro CLI)", None),
    (".pi/agent/skills", "~/.pi/agent/skills/ (Pi)", None),
    (".agents/skills", "~/.agents/skills/ (OpenCode, Aider, Droid, generic)", None),
]


def install_global_skills(mode: str) -> None:
    for rel, label, subset in GLOBAL_AGENT_DIRS:
        target = HOME / rel
        # Only provision agents that exist on this machine — don't scaffold
        # skill dirs for tools the user never installed.
        if not target.parent.is_dir():
            continue
        install_skills(target, label, subset=subset, mode=mode)
    _install_hermes_profiles(mode)


def _agent_install_dirs() -> list[tuple[Path, str]]:
    """Every agent skills dir to inspect, with its display label.

    Mirrors what `install_global_skills` provisions — including Hermes wherever
    HERMES_HOME actually points. On Windows that is %LOCALAPPDATA%\\hermes, so
    reporting against ~/.hermes alone calls an installed Hermes "not installed".
    """
    hermes_home = os.environ.get("HERMES_HOME") or _read_config_value("HERMES_HOME")
    hermes_dir = Path(hermes_home).expanduser() if hermes_home else None
    relocated = bool(hermes_dir) and hermes_dir != HOME / ".hermes"

    dirs: list[tuple[Path, str]] = []
    for rel, label, _subset in GLOBAL_AGENT_DIRS:
        if rel == ".hermes/skills" and relocated:
            dirs.append((hermes_dir / "skills", f"{hermes_dir}/skills/ (Hermes active profile)"))
        else:
            dirs.append((HOME / rel, label))

    profiles = HOME / ".hermes" / "profiles"
    if profiles.is_dir():
        for prof in sorted(p for p in profiles.iterdir() if p.is_dir()):
            dirs.append(
                (
                    prof / "skills",
                    f"~/.hermes/profiles/{prof.name}/skills/ (Hermes profile: {prof.name})",
                )
            )
    return dirs


def _install_hermes_profiles(mode: str) -> None:
    """Install into the active and all named Hermes profiles."""
    hermes_home = os.environ.get("HERMES_HOME") or _read_config_value("HERMES_HOME")
    handled: set[Path] = set()
    if hermes_home:
        hp = Path(hermes_home).expanduser()
        if hp != HOME / ".hermes" and hp.is_dir():
            install_skills(hp / "skills", f"{hp}/skills/ (Hermes active profile)", mode=mode)
            handled.add(hp)
    profiles = HOME / ".hermes" / "profiles"
    if profiles.is_dir():
        for prof in sorted(p for p in profiles.iterdir() if p.is_dir()):
            if prof in handled:
                continue
            install_skills(
                prof / "skills",
                f"~/.hermes/profiles/{prof.name}/skills/ (Hermes profile: {prof.name})",
                mode=mode,
            )


# ── Config ───────────────────────────────────────────────────────────────────
def _parse_config(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _read_config() -> dict[str, str]:
    return _parse_config(GLOBAL_CONFIG)


def _read_config_value(key: str) -> str:
    return _read_config().get(key, "")


def resolve_vault_path(cli_vault: str | None) -> str:
    if cli_vault:
        return os.path.expanduser(cli_vault)
    existing = _read_config_value("OBSIDIAN_VAULT_PATH")
    if existing and existing != "/path/to/your/vault":
        return existing
    if sys.stdin.isatty():
        try:
            entered = input("  Vault folder (an existing vault, or where to create one): ").strip()
        except EOFError:
            entered = ""
        if entered:
            return os.path.expanduser(entered)
    return existing


def write_config(vault_path: str, extra: dict[str, str] | None = None) -> None:
    """Write ~/.llm-wiki/config, preserving unknown keys.

    Existing values are kept (this config carries user-managed keys like
    OBSIDIAN_SOURCES_DIR); *extra* sets or overrides keys the caller decided.
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    values = _read_config()
    values.update(extra or {})
    if vault_path:
        values["OBSIDIAN_VAULT_PATH"] = vault_path
    # LLM_WIKI_REPO points at the repo root so skills that reference framework
    # assets (templates, references) can find them post-install.
    values["LLM_WIKI_REPO"] = str(skills_dir().parent)
    values["LLM_WIKI_VERSION"] = __version__
    GLOBAL_CONFIG.write_text(
        "".join(f'{key}="{value}"\n' for key, value in values.items()),
        encoding="utf-8",
    )
    print(f"✅  Global config written to {GLOBAL_CONFIG}")


def _check_stale() -> None:
    """Warn if setup hasn't run for this version, or if skills are missing."""
    if not GLOBAL_CONFIG.is_file():
        print(
            f"⚠️  llm-wiki {__version__} is installed but setup has never been run.\n"
            f"   Run: llm-wiki setup --vault /path/to/your/vault",
            file=sys.stderr,
        )
        return

    setup_version = _read_config_value("LLM_WIKI_VERSION")
    if setup_version and setup_version != __version__:
        print(
            f"⚠️  llm-wiki upgraded {setup_version} → {__version__} but setup hasn't been re-run.\n"
            f"   New skills won't be available until you run: llm-wiki setup",
            file=sys.stderr,
        )
        return

    # Even if the version matches, check that ~/.claude/skills has the full set.
    claude_skills_dir = HOME / ".claude" / "skills"
    if claude_skills_dir.is_dir():
        bundled = set(list_skills())
        installed = {p.name for p in claude_skills_dir.iterdir() if p.is_dir()}
        missing = bundled - installed
        if missing:
            print(
                f"⚠️  {len(missing)} skill(s) missing from ~/.claude/skills/ "
                f"(e.g. {', '.join(sorted(missing)[:3])}{', ...' if len(missing) > 3 else ''}).\n"
                f"   Run: llm-wiki setup",
                file=sys.stderr,
            )


# ── Doctor ───────────────────────────────────────────────────────────────────
def _doctor_add(
    checks: list[dict[str, str]],
    *,
    name: str,
    status: str,
    detail: str,
    hint: str = "",
) -> None:
    checks.append({
        "name": name,
        "status": status,
        "detail": detail,
        "hint": hint,
    })


def _doctor_status(checks: list[dict[str, str]]) -> str:
    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _required_vault_paths(vault: Path) -> list[Path]:
    return [
        vault / "index.md",
        vault / "log.md",
        vault / "hot.md",
        vault / ".manifest.json",
    ]


def _extra_required_files(config: dict[str, str]) -> list[str]:
    """Vault-relative paths the owner declared mandatory via WIKI_REQUIRED_FILES."""
    raw = config.get("WIKI_REQUIRED_FILES", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _check_required_files(vault: Path, required: list[str]) -> dict[str, str] | None:
    """Fail-level check for owner-declared required files (opt-in, so missing = fail)."""
    if not required:
        return None
    missing = [rel for rel in required if not (vault / rel).exists()]
    if missing:
        return {
            "name": "required-files",
            "status": "fail",
            "detail": f"missing {len(missing)} required file(s): {', '.join(missing)}",
            "hint": "restore from git or recreate; declared in WIKI_REQUIRED_FILES",
        }
    return {
        "name": "required-files",
        "status": "pass",
        "detail": f"all {len(required)} WIKI_REQUIRED_FILES present",
        "hint": "",
    }


def _check_layout(vault: Path) -> dict[str, str]:
    """The CATEGORIES table in AGENTS.md parses, and its folders exist.

    A vault without the table keeps the original layout; its folders are not
    checked, because vaults made before the table often lack a few of them.
    """
    from llm_wiki.layout import LayoutError, load_layout

    try:
        layout = load_layout(vault)
    except LayoutError as exc:
        return {
            "name": "vault-layout",
            "status": "fail",
            "detail": "CATEGORIES table in AGENTS.md is invalid: " + "; ".join(exc.problems),
            "hint": "fix the table: one row per folder, with Folder, Holds and Role columns",
        }
    folders = ", ".join(f"{category.folder}/" for category in layout.categories)
    if layout.source != "AGENTS.md":
        return {
            "name": "vault-layout",
            "status": "pass",
            "detail": f"no CATEGORIES table in AGENTS.md; using the original layout ({folders})",
            "hint": "",
        }
    missing = [category.folder for category in layout.categories if not (vault / category.folder).is_dir()]
    if missing:
        return {
            "name": "vault-layout",
            "status": "warn",
            "detail": "category folder(s) missing: " + ", ".join(f"{name}/" for name in missing),
            "hint": "create them, or remove their rows from the CATEGORIES table in AGENTS.md",
        }
    count = len(layout.categories)
    return {
        "name": "vault-layout",
        "status": "pass",
        "detail": f"{count} {'category' if count == 1 else 'categories'} from AGENTS.md: {folders}",
        "hint": "",
    }


def _check_git_tree(vault: Path) -> dict[str, str] | None:
    """Tripwire for uncommitted changes in a git-backed vault.

    Warn, not fail: a dirty tree is expected mid-operation; it only signals
    trouble when found at session start by an agent that didn't make the
    changes (the vault constitution's law 9).
    """
    if not (vault / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(vault), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return {
            "name": "git-tree",
            "status": "warn",
            "detail": f"git status failed: {proc.stderr.strip()[:120]}",
            "hint": "check the vault's git repository health",
        }
    dirty = [line for line in proc.stdout.splitlines() if line.strip()]
    if not dirty:
        return {"name": "git-tree", "status": "pass", "detail": "working tree clean", "hint": ""}
    detail = f"{len(dirty)} uncommitted change(s)"
    log_path = vault / "log.md"
    if log_path.is_file():
        try:
            entries = [
                line
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.startswith("- [")
            ]
        except OSError:
            entries = []
        if entries:
            detail += f"; last logged op: {entries[-1][2:150]}"
    return {
        "name": "git-tree",
        "status": "warn",
        "detail": detail,
        "hint": "law 9: if you did not make these changes, stop and report to the owner",
    }


def run_doctor(*, vault_override: str | None = None) -> dict[str, object]:
    checks: list[dict[str, str]] = []

    try:
        bundled = list_skills()
        _doctor_add(
            checks,
            name="bundled-skills",
            status="pass" if bundled else "fail",
            detail=f"{len(bundled)} skill(s) available in {skills_dir()}",
            hint="" if bundled else "check the skills/ folder in the llm-wiki repo",
        )
    except FileNotFoundError as exc:
        _doctor_add(checks, name="bundled-skills", status="fail", detail=str(exc), hint="reinstall llm-wiki")
        bundled = []

    config = _read_config()
    config_present = GLOBAL_CONFIG.is_file()
    _doctor_add(
        checks,
        name="global-config",
        status="pass" if config_present else "fail",
        detail=str(GLOBAL_CONFIG) if config_present else "global config not written",
        hint="" if config_present else "run: llm-wiki setup --vault /path/to/your/vault",
    )

    vault_path = ""
    if vault_override:
        vault_path = os.path.expanduser(vault_override)
    elif config_present:
        vault_path = config.get("OBSIDIAN_VAULT_PATH", "")

    if not vault_path:
        _doctor_add(
            checks,
            name="vault-config",
            status="fail",
            detail="OBSIDIAN_VAULT_PATH is not set",
            hint="run: llm-wiki setup --vault /path/to/your/vault",
        )
        vault = None
    else:
        vault = Path(vault_path).expanduser().resolve()
        _doctor_add(
            checks,
            name="vault-config",
            status="pass",
            detail=str(vault),
            hint="",
        )

    setup_version = config.get("LLM_WIKI_VERSION", "") if config_present else ""
    if setup_version and setup_version != __version__:
        _doctor_add(
            checks,
            name="setup-version",
            status="warn",
            detail=f"setup ran with {setup_version}; installed package is {__version__}",
            hint="run: llm-wiki setup",
        )
    elif config_present:
        _doctor_add(
            checks,
            name="setup-version",
            status="pass",
            detail=f"setup version matches installed package ({__version__})" if setup_version else "setup version not recorded",
            hint="" if setup_version else "re-run setup to record install metadata",
        )

    if vault is not None:
        if vault.is_dir():
            _doctor_add(checks, name="vault-path", status="pass", detail="vault directory exists", hint="")
            missing_core = [str(path.relative_to(vault)) for path in _required_vault_paths(vault) if not path.exists()]
            if missing_core:
                _doctor_add(
                    checks,
                    name="vault-core-files",
                    status="warn",
                    detail=f"missing {len(missing_core)} core file(s): {', '.join(missing_core)}",
                    hint="run the wiki setup skill or create the missing files",
                )
            else:
                _doctor_add(checks, name="vault-core-files", status="pass", detail="core vault files present", hint="")

            checks.append(_check_layout(vault))

            manifest_path = vault / ".manifest.json"
            if manifest_path.exists():
                try:
                    data = json.loads(manifest_path.read_text(encoding="utf-8"))
                    sources = data.get("sources", {})
                    _doctor_add(
                        checks,
                        name="manifest-json",
                        status="pass",
                        detail=f"valid JSON with {len(sources)} tracked source(s)",
                        hint="",
                    )
                except (json.JSONDecodeError, OSError) as exc:
                    _doctor_add(
                        checks,
                        name="manifest-json",
                        status="fail",
                        detail=f"invalid manifest: {exc}",
                        hint="repair or regenerate .manifest.json",
                    )

            required_check = _check_required_files(vault, _extra_required_files(config))
            if required_check:
                checks.append(required_check)
            git_check = _check_git_tree(vault)
            if git_check:
                checks.append(git_check)
        else:
            _doctor_add(
                checks,
                name="vault-path",
                status="fail",
                detail=f"vault directory not found: {vault}",
                hint="fix OBSIDIAN_VAULT_PATH or re-run setup",
            )

    agent_summaries: list[str] = []
    partial_agents: list[str] = []
    full_agents = 0
    bundled_set = set(bundled)
    for agent_dir, label in _agent_install_dirs():
        if not agent_dir.is_dir():
            continue
        installed = {p.name for p in agent_dir.iterdir() if (p.is_dir() or p.is_symlink())}
        missing = bundled_set - installed
        count = len(installed & bundled_set)
        agent_summaries.append(f"{label}: {count}/{len(bundled_set)}")
        if missing:
            partial_agents.append(label)
        else:
            full_agents += 1

    if not agent_summaries:
        _doctor_add(
            checks,
            name="agent-installs",
            status="warn",
            detail="no global agent skill installs found",
            hint="run: llm-wiki setup",
        )
    elif partial_agents:
        _doctor_add(
            checks,
            name="agent-installs",
            status="warn",
            detail="; ".join(agent_summaries),
            hint="re-run llm-wiki setup to fill missing skills",
        )
    else:
        _doctor_add(
            checks,
            name="agent-installs",
            status="pass",
            detail=f"{full_agents} agent install(s) fully provisioned",
            hint="",
        )

    return {
        "status": _doctor_status(checks),
        "checks": checks,
    }


def _print_doctor(report: dict[str, object]) -> None:
    icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
    print(f"llm-wiki doctor: {report['status']}")
    for check in report["checks"]:
        name = check["name"]
        status = check["status"]
        detail = check["detail"]
        hint = check["hint"]
        print(f"{icon.get(status, '•')} {name}: {detail}")
        if hint:
            print(f"   hint: {hint}")


def _is_new_vault_spot(target: Path) -> bool:
    return not target.exists() or (target.is_dir() and not any(target.iterdir()))


def _offer_new_vault(vault_path: str) -> dict[str, str]:
    """When the vault folder doesn't exist yet, offer to create it.

    Runs the same interview as `llm-wiki init` on a terminal. Returns config
    keys to write (the staged-writes choice), or {} when nothing was created.
    """
    from llm_wiki.scaffold import ScaffoldError, create_vault, interview, next_steps

    target = Path(vault_path).expanduser().absolute()
    if not _is_new_vault_spot(target):
        return {}
    if not sys.stdin.isatty():
        print(f"    → No vault at {target} yet. Create one with: llm-wiki init \"{target}\"")
        return {}
    try:
        answer = input(f"  No vault at {target} yet. Create one now? [Y/n] ").strip().lower()
    except EOFError:
        answer = "n"
    if answer not in ("", "y", "yes"):
        print(f"    → Create it later with: llm-wiki init \"{target}\"")
        return {}
    print()
    choices = interview(target=target)
    if choices is None:
        print("    → No vault created.")
        return {}
    try:
        summary = create_vault(target, choices.plan, demo=choices.demo, backup_hook=choices.backup_hook)
    except ScaffoldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return {}
    print()
    print(next_steps(summary, choices.plan, from_setup=True))
    print()
    default = choices.plan.suggests_staged_writes()
    prompt = "  Hold agent edits in _staging/ until you approve them (staged writes)? " + ("[Y/n] " if default else "[y/N] ")
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        answer = ""
    staged = default if not answer else answer in ("y", "yes")
    print()
    return {"WIKI_STAGED_WRITES": "true" if staged else "false"}


# ── Commands ─────────────────────────────────────────────────────────────────
def cmd_init(args: argparse.Namespace) -> int:
    from llm_wiki.presets import DEFAULT_PACK, PresetError, compose
    from llm_wiki.scaffold import ScaffoldError, check_target, create_vault, interview, next_steps, render_preview

    target = Path(args.path).expanduser().absolute()
    asked = any([args.pack, args.role, args.add, args.folder, args.rename, args.no_demo, args.backup_hook])
    try:
        check_target(target)
        if not (asked or args.yes or args.dry_run) and sys.stdin.isatty():
            choices = interview(target=target)
            if choices is None:
                print("Cancelled; nothing was written.")
                return 1
            plan, demo, backup_hook = choices.plan, choices.demo, choices.backup_hook
        else:
            plan = compose(
                args.pack or DEFAULT_PACK,
                roles=args.role or (),
                addons=args.add or (),
                folders=[_pair(value, "--folder", "name=what it holds") for value in args.folder or ()],
                renames=[_pair(value, "--rename", "old=new") for value in args.rename or ()],
            )
            demo, backup_hook = not args.no_demo, args.backup_hook
            if args.dry_run:
                print(render_preview(target, plan, demo=demo, backup_hook=backup_hook))
                return 0
        summary = create_vault(target, plan, demo=demo, backup_hook=backup_hook)
    except (PresetError, ScaffoldError) as exc:
        problems = getattr(exc, "problems", [str(exc)])
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return 1
    print(next_steps(summary, plan))
    return 0


def _pair(value: str, flag: str, shape: str) -> tuple[str, str]:
    from llm_wiki.presets import PresetError

    left, sep, right = value.partition("=")
    if not sep:
        raise PresetError([f"{flag} takes {shape}, got `{value}`"])
    return left, right


def cmd_presets(args: argparse.Namespace) -> int:
    from llm_wiki.presets import ADDONS, DEFAULT_PACK, PACKS, ROLES, catalog

    if args.json:
        print(json.dumps(catalog(), indent=2 if args.pretty else None))
        return 0
    print("Packs (llm-wiki init PATH --pack NAME)")
    for pack in PACKS.values():
        folders = " ".join(f"{folder.folder}/" for folder in pack.folders)
        default = "  (default)" if pack.name == DEFAULT_PACK else ""
        print(f"  {pack.name:<9} {folders:<44} {pack.summary}{default}")
    print()
    print("Roles for the standard pack; combine any (--role NAME)")
    for role in ROLES.values():
        adds = " ".join(f"{ADDONS[name].folder}/" for name in role.adds)
        print(f"  {role.name:<13} + {adds:<22} {role.label}: {role.summary}")
    print()
    print("Single add-on folders (--add NAME), or your own (--folder name=\"what it holds\")")
    print("  " + "  ".join(ADDONS))
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    mode = "copy" if args.copy else "symlink"
    print("\n╔══════════════════════════════════════════════════╗")
    print("║           llm-wiki — Agent Setup                 ║")
    print("╚══════════════════════════════════════════════════╝\n")

    vault_path = resolve_vault_path(args.vault)
    extra = _offer_new_vault(vault_path) if vault_path else {}
    write_config(vault_path, extra)
    if not vault_path:
        print("    → Vault path not set yet. Re-run with `--vault /path/to/vault`")
        print("      or edit OBSIDIAN_VAULT_PATH in ~/.llm-wiki/config.")

    print()
    install_global_skills(mode)

    n = len(list_skills())
    print("\n───────────────────────────────────────────────────")
    print(" Setup complete!\n")
    print(f" Skills installed: {n}  (mode: {mode})")
    if vault_path:
        print(f" Vault:            {vault_path}")
    print("\n From any project:")
    print("   /wiki-update    → sync knowledge into your vault")
    print("   /wiki-query     → ask questions against your wiki")
    print("───────────────────────────────────────────────────\n")
    return 0


def cmd_graph_query(args: argparse.Namespace) -> int:
    from llm_wiki.graphrag import query
    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"error: vault not found: {vault}", file=sys.stderr)
        return 1
    result = query(vault, args.question, top_n=args.top, max_should_read=args.max_read)
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def cmd_batch_plan(args: argparse.Namespace) -> int:
    from llm_wiki.batch import plan_batches
    source_dir = Path(args.source_dir).expanduser().resolve()
    vault = Path(args.vault).expanduser().resolve()
    if not source_dir.is_dir():
        print(f"error: source directory not found: {source_dir}", file=sys.stderr)
        return 1
    result = plan_batches(
        source_dir,
        vault,
        max_batch_mb=args.max_mb,
        max_batch_files=args.max_files,
        skip_unchanged=not args.no_cache,
        include_code=args.include_code,
    )
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def cmd_graph_analyse(args: argparse.Namespace) -> int:
    from llm_wiki.graph_analysis import analyse_vault
    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"error: vault not found: {vault}", file=sys.stderr)
        return 1
    result = analyse_vault(vault, top_n=args.top)
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def cmd_cache_check(args: argparse.Namespace) -> int:
    from llm_wiki.cache import check_sources
    vault = Path(args.vault).expanduser().resolve()
    sources = [Path(p).expanduser().resolve() for p in args.sources]
    result = check_sources(vault, sources)
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def cmd_cache_update(args: argparse.Namespace) -> int:
    from llm_wiki.cache import update_source
    vault = Path(args.vault).expanduser().resolve()
    source = Path(args.source).expanduser().resolve()
    h = update_source(
        vault,
        source,
        pages_created=args.created or [],
        pages_updated=args.updated or [],
    )
    print(json.dumps({"path": str(source), "content_hash": h}))
    return 0


def cmd_cache_hash(args: argparse.Namespace) -> int:
    from llm_wiki.cache import hash_file
    path = Path(args.path).expanduser().resolve()
    if not path.exists():
        print(f"error: {path} does not exist", file=sys.stderr)
        return 1
    print(json.dumps({"path": str(path), "sha256": hash_file(path)}))
    return 0


def cmd_ast_extract(args: argparse.Namespace) -> int:
    from llm_wiki.ast_extractor import extract
    path = Path(args.path).expanduser().resolve()
    try:
        result = extract(path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def cmd_pdf_extract(args: argparse.Namespace) -> int:
    from llm_wiki.pdf_extract import extract_pdf
    path = Path(args.path).expanduser().resolve()
    cache_dir = Path(args.cache_dir).expanduser().resolve() if args.cache_dir else None
    try:
        result = extract_pdf(
            path,
            cache_dir=cache_dir,
            ocr=not args.no_ocr,
            dpi=args.dpi,
            language=args.language,
            tessdata=args.tessdata,
            force=args.force,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.pretty:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    report = run_doctor(vault_override=args.vault)
    if args.json:
        if args.pretty:
            print(json.dumps(report, indent=2))
        else:
            print(json.dumps(report))
    else:
        _print_doctor(report)
    statuses = {check["status"] for check in report["checks"]}
    if "fail" in statuses or (args.strict and "warn" in statuses):
        return 1
    return 0


def _print_lint(report: dict[str, object]) -> None:
    print(f"llm-wiki lint: {report['status']}")
    layout = report["layout"]
    print(f"layout: {layout['source']} ({', '.join(f'{name}/' for name in layout['folders'])})")
    stats = report["stats"]
    print(f"pages: {stats['pages']}  links: {stats['link_count']}")
    for name, count in stats["findings"].items():
        print(f"{name}: {count}")


def cmd_lint(args: argparse.Namespace) -> int:
    from llm_wiki.lint import lint_vault

    vault = _resolve_vault_arg(args.vault)
    if vault is None:
        return 1

    report = lint_vault(vault)
    if args.json:
        if args.pretty:
            print(json.dumps(report, indent=2))
        else:
            print(json.dumps(report))
    else:
        _print_lint(report)
    if report["status"] == "fail" or (args.strict and report["status"] == "warn"):
        return 1
    return 0


def _resolve_vault_arg(vault_arg: str | None) -> Path | None:
    """The vault from an explicit argument or the global config, if it exists."""
    vault_arg = vault_arg or _read_config_value("OBSIDIAN_VAULT_PATH")
    if not vault_arg:
        print("error: vault not configured; pass a path or run llm-wiki setup", file=sys.stderr)
        return None
    vault = Path(vault_arg).expanduser().resolve()
    if not vault.is_dir():
        print(f"error: vault not found: {vault}", file=sys.stderr)
        return None
    return vault


def cmd_layout(args: argparse.Namespace) -> int:
    from llm_wiki.layout import LayoutError, load_layout

    vault = _resolve_vault_arg(args.vault)
    if vault is None:
        return 1
    try:
        layout = load_layout(vault)
    except LayoutError as exc:
        print("error: the CATEGORIES table in AGENTS.md is invalid:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(layout.to_dict(), indent=2 if args.pretty else None))
        return 0

    source = "CATEGORIES table in AGENTS.md" if layout.source == "AGENTS.md" else "original layout (no CATEGORIES table)"
    print(f"layout: {source}")
    width = max(len(category.folder) for category in layout.categories) + 1
    for category in layout.categories:
        role = category.role or "-"
        print(f"  {category.folder + '/':<{width + 1}} {role:<10} {category.holds}")
    print(f"catch-all: {layout.catch_all.folder}/")
    print("roles: " + "  ".join(f"{role}→{folder}/" for role, folder in layout.roles().items()))
    return 0


def _print_query(result: dict[str, object]) -> None:
    print(f"answer_type: {result['answer_type']}")
    candidates = result.get("candidates", [])
    if candidates:
        print("candidates:")
        for item in candidates:
            print(f"- {item['title']} ({item['page']}) score={item['score']}")
    path = result.get("path") or []
    if path:
        print("path:")
        print(" -> ".join(path))
    should_read = result.get("should_read") or []
    if should_read:
        print("should_read:")
        for page in should_read:
            print(f"- {page}")


def cmd_query(args: argparse.Namespace) -> int:
    from llm_wiki.graphrag import query

    vault_arg = args.vault or _read_config_value("OBSIDIAN_VAULT_PATH")
    if not vault_arg:
        print("error: vault not configured; pass --vault or run llm-wiki setup", file=sys.stderr)
        return 1

    vault = Path(vault_arg).expanduser().resolve()
    if not vault.is_dir():
        print(f"error: vault not found: {vault}", file=sys.stderr)
        return 1

    result = query(vault, args.question, top_n=args.top, max_should_read=args.max_read)
    if args.json:
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
    else:
        _print_query(result)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    for name in list_skills():
        print(name)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    bundled = list_skills()
    print(f"llm-wiki {__version__}")
    print(f"skills:    {skills_dir()}")
    print(f"config:    {GLOBAL_CONFIG}{'' if GLOBAL_CONFIG.exists() else ' (not written yet)'}")
    if GLOBAL_CONFIG.exists():
        vp = _read_config_value("OBSIDIAN_VAULT_PATH")
        setup_ver = _read_config_value("LLM_WIKI_VERSION")
        print(f"vault:     {vp or '(unset)'}")
        print(f"setup ran: {setup_ver or '(never)'}")
    print(f"bundled skills: {len(bundled)}")
    print()
    print("Agent skill install status:")
    bundled_set = set(bundled)
    for agent_dir, label in _agent_install_dirs():
        if not agent_dir.is_dir():
            print(f"  {label}: not installed")
            continue
        installed = {p.name for p in agent_dir.iterdir() if p.is_dir()}
        wiki_installed = installed & bundled_set
        missing = bundled_set - installed
        status = "✅" if not missing else "⚠️ "
        print(f"  {status} {label}: {len(wiki_installed)}/{len(bundled_set)}", end="")
        if missing:
            print(f"  (run: llm-wiki setup)", end="")
        print()
    _check_stale()
    return 0


# ── Argument parsing ─────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm-wiki",
        description="LLM-Wiki agent skills: installer and vault helper commands.",
    )
    p.add_argument("-V", "--version", action="version", version=f"llm-wiki {__version__}")
    sub = p.add_subparsers(dest="command")

    sp = sub.add_parser("setup", help="install skills into your agents and write config")
    sp.add_argument("--vault", metavar="PATH", help="absolute path to your Obsidian vault")
    sp.add_argument(
        "--copy",
        action="store_true",
        help="copy skill files instead of symlinking to the repo checkout",
    )
    sp.set_defaults(func=cmd_setup)

    from llm_wiki.presets import ADDONS, PACKS, ROLES

    np = sub.add_parser(
        "init",
        help="create a new vault from a pack (asks a few questions when run in a terminal without options)",
    )
    np.add_argument("path", help="where to create the vault: a new or empty folder")
    np.add_argument("--pack", choices=list(PACKS), help="standard (default) or minimal")
    np.add_argument(
        "--role", action="append", choices=list(ROLES), metavar="ROLE",
        help=f"add the folders one kind of work needs; repeatable ({', '.join(ROLES)})",
    )
    np.add_argument(
        "--add", action="append", choices=list(ADDONS), metavar="FOLDER",
        help=f"add one add-on folder; repeatable ({', '.join(ADDONS)})",
    )
    np.add_argument(
        "--folder", action="append", metavar="NAME=HOLDS",
        help='add a folder of your own, e.g. --folder recipes="Cooking recipes: ingredients and steps"',
    )
    np.add_argument("--rename", action="append", metavar="OLD=NEW", help="rename a folder, e.g. --rename concepts=notes")
    np.add_argument("--no-demo", action="store_true", help="skip the demo pages")
    np.add_argument("--backup-hook", action="store_true", help="add a post-commit hook that pushes to your git remote")
    np.add_argument("--dry-run", action="store_true", help="show the folders and CATEGORIES table without writing")
    np.add_argument("--yes", action="store_true", help="never ask questions; use the options given (default: standard)")
    np.set_defaults(func=cmd_init)

    pr = sub.add_parser("presets", help="list the packs, roles, and add-on folders init can use")
    pr.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    pr.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    pr.set_defaults(func=cmd_presets)

    lp = sub.add_parser("list", help="list bundled skills")
    lp.set_defaults(func=cmd_list)

    ip = sub.add_parser("info", help="show install paths, version, and config")
    ip.set_defaults(func=cmd_info)

    gq = sub.add_parser(
        "graph-query",
        help="answer a question from the vault's wikilink index without reading page bodies",
    )
    gq.add_argument("vault", help="path to the Obsidian vault")
    gq.add_argument("question", help="question to answer")
    gq.add_argument("--top", type=int, default=8, help="number of candidate pages to rank (default: 8)")
    gq.add_argument("--max-read", type=int, default=3, help="max pages to return in should_read (default: 3)")
    gq.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    gq.set_defaults(func=cmd_graph_query)

    bp = sub.add_parser(
        "batch-plan",
        help="split a source directory into parallel-ingest batches, skipping unchanged files",
    )
    bp.add_argument("vault", help="path to the Obsidian vault")
    bp.add_argument("source_dir", help="directory of source documents to ingest")
    bp.add_argument("--max-mb", type=float, default=2.0, help="max MB per batch (default: 2)")
    bp.add_argument("--max-files", type=int, default=20, help="max files per batch (default: 20)")
    bp.add_argument("--no-cache", action="store_true", help="disable manifest-based skip of unchanged files")
    bp.add_argument("--include-code", action="store_true", help="include code files (default: excluded; use ast-extract instead)")
    bp.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    bp.set_defaults(func=cmd_batch_plan)

    ga = sub.add_parser(
        "graph-analyse",
        help="analyse the vault's wikilink graph: god nodes, communities, surprising connections",
    )
    ga.add_argument("vault", help="path to the Obsidian vault")
    ga.add_argument("--top", type=int, default=20, help="number of top results to return (default: 20)")
    ga.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    ga.set_defaults(func=cmd_graph_analyse)

    cc = sub.add_parser(
        "cache-check",
        help="check which sources are new/modified/unchanged vs. .manifest.json",
    )
    cc.add_argument("vault", help="path to the Obsidian vault")
    cc.add_argument("sources", nargs="+", help="source file or directory paths to check")
    cc.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    cc.set_defaults(func=cmd_cache_check)

    cu = sub.add_parser(
        "cache-update",
        help="record a source's current SHA-256 hash in .manifest.json after ingestion",
    )
    cu.add_argument("vault", help="path to the Obsidian vault")
    cu.add_argument("source", help="source file or directory that was just ingested")
    cu.add_argument("--created", nargs="*", metavar="PAGE", help="vault-relative paths of pages this ingest created")
    cu.add_argument("--updated", nargs="*", metavar="PAGE", help="vault-relative paths of pages this ingest updated")
    cu.set_defaults(func=cmd_cache_update)

    ch = sub.add_parser(
        "cache-hash",
        help="compute the SHA-256 hash of a file or directory (no manifest I/O)",
    )
    ch.add_argument("path", help="file or directory to hash")
    ch.set_defaults(func=cmd_cache_hash)

    ap = sub.add_parser(
        "ast-extract",
        help="extract code structure (classes, functions, imports) from a file or directory — no LLM, no API calls",
    )
    ap.add_argument("path", help="file or directory to extract from")
    ap.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    ap.set_defaults(func=cmd_ast_extract)

    pe = sub.add_parser(
        "pdf-extract",
        help="pull a PDF's text layer locally (OCR when available) so ingest vision-reads only the pages that need it",
    )
    pe.add_argument("path", help="PDF file to extract")
    pe.add_argument("--cache-dir", help="override the cache location (default: ~/.llm-wiki/cache/pdf)")
    pe.add_argument("--no-ocr", action="store_true", help="skip OCR; report image-only pages as needs_vision")
    pe.add_argument("--dpi", type=int, default=300, help="OCR render DPI (default: 300)")
    pe.add_argument("--language", default="eng", help="Tesseract language code (default: eng)")
    pe.add_argument("--tessdata", help="explicit tessdata directory (default: TESSDATA_PREFIX, then standard install paths)")
    pe.add_argument("--force", action="store_true", help="re-extract even if a cache entry exists")
    pe.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    pe.set_defaults(func=cmd_pdf_extract)

    dr = sub.add_parser(
        "doctor",
        help="check config, vault shape, and installed skills",
    )
    dr.add_argument("--vault", help="override OBSIDIAN_VAULT_PATH for this health check")
    dr.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    dr.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    dr.add_argument("--strict", action="store_true", help="exit non-zero on warnings as well as failures")
    dr.set_defaults(func=cmd_doctor)

    lt = sub.add_parser(
        "lint",
        help="lint a vault for missing frontmatter, broken links, invalid lifecycle states, duplicates, and orphans",
    )
    lt.add_argument("vault", nargs="?", help="path to the Obsidian vault (defaults to configured OBSIDIAN_VAULT_PATH)")
    lt.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    lt.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    lt.add_argument("--strict", action="store_true", help="exit non-zero on warnings as well as failures")
    lt.set_defaults(func=cmd_lint)

    ly = sub.add_parser(
        "layout",
        help="show the vault's page folders (CATEGORIES table in AGENTS.md) and which folder plays each role",
    )
    ly.add_argument("vault", nargs="?", help="path to the vault (defaults to configured OBSIDIAN_VAULT_PATH)")
    ly.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ly.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    ly.set_defaults(func=cmd_layout)

    qq = sub.add_parser(
        "query",
        help="query the configured vault without passing the raw path each time",
    )
    qq.add_argument("question", help="question to ask against the vault index")
    qq.add_argument("--vault", help="override OBSIDIAN_VAULT_PATH for this query")
    qq.add_argument("--top", type=int, default=8, help="number of candidate pages to rank (default: 8)")
    qq.add_argument("--max-read", type=int, default=3, help="max pages to return in should_read (default: 3)")
    qq.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    qq.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    qq.set_defaults(func=cmd_query)

    return p


def main(argv: list[str] | None = None) -> int:
    # Emoji output must not crash on legacy Windows console code pages.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, OSError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    # Warn about stale installs on every command except `setup` (which fixes it),
    # `info` (which calls _check_stale itself), `doctor` (which reports it), and
    # `init`/`presets`, which commonly run before setup ever has.
    if getattr(args, "command", None) not in ("setup", "info", "doctor", "init", "presets", None):
        _check_stale()
    try:
        return args.func(args)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
