"""Tests for `llm-wiki init`: writing a vault, its preview, and its interview.

The promise under test: every pack and role combination, with or without demo
pages, writes a vault that passes the gate (no fail-level lint findings) the
moment it exists.

Stdlib unittest only — the repo has no runtime dependencies and the test
suite keeps it that way. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from llm_wiki.cli import _check_layout, main
from llm_wiki.layout import load_layout
from llm_wiki.lint import FAIL_FINDINGS, lint_vault
from llm_wiki.presets import DEMO_PAGES, ROLES, compose
from llm_wiki.scaffold import (
    TABLE_MARKER,
    ScaffoldError,
    create_vault,
    interview,
    next_steps,
    presets_dir,
    render_preview,
)

NOW = datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc)


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class PresetsFolderTests(unittest.TestCase):
    def test_base_agents_file_keeps_the_table_marker(self):
        self.assertIn(TABLE_MARKER, (presets_dir() / "base" / "AGENTS.md").read_text(encoding="utf-8"))

    def test_every_template_and_demo_page_exists(self):
        root = presets_dir()
        for plan in (compose("standard", roles=ROLES), compose("minimal")):
            for row in plan.rows:
                with self.subTest(template=row.template):
                    self.assertTrue((root / "templates" / f"{row.template}.md").is_file())
        for slug in DEMO_PAGES:
            with self.subTest(demo=slug):
                self.assertTrue((root / "demo" / f"{slug}.md").is_file())

    def test_base_files_never_link_to_demo_pages(self):
        # Base files ship in every vault, including ones without demo pages.
        for path in (presets_dir() / "base").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for slug in DEMO_PAGES:
                with self.subTest(file=path.name, slug=slug):
                    self.assertNotIn(f"[[{slug}", text)


class CreateVaultGateTests(TempDirTestCase):
    """Every combination is born passing the gate."""

    def assertGatePasses(self, vault: Path) -> dict:
        report = lint_vault(vault)
        failing = {name: report["findings"][name] for name in FAIL_FINDINGS if report["findings"][name]}
        self.assertEqual(failing, {})
        self.assertEqual(report["findings"]["orphan_pages"], [])
        self.assertEqual(report["findings"]["missing_summaries"], [])
        # The one tolerated warning: page templates share the {{title}} placeholder.
        for duplicate in report["findings"]["duplicate_titles"]:
            self.assertEqual(duplicate["title"], "{{title}}")
        self.assertEqual(_check_layout(vault)["status"], "pass")
        return report

    def test_every_combination(self):
        combos = [("minimal", ())] + [("standard", ())] + [("standard", (role,)) for role in ROLES]
        combos.append(("standard", tuple(ROLES)))
        for number, (pack, roles) in enumerate(combos):
            for demo in (True, False):
                with self.subTest(pack=pack, roles=roles, demo=demo):
                    vault = self.root / f"v{number}-{demo}"
                    plan = compose(pack, roles=roles)
                    create_vault(vault, plan, demo=demo, now=NOW)
                    self.assertGatePasses(vault)
                    self.assertEqual(load_layout(vault).categories, plan.categories)
                    for folder in plan.folders:
                        self.assertTrue((vault / folder).is_dir())

    def test_minimal_vault_is_spotless(self):
        vault = self.root / "v"
        create_vault(vault, compose("minimal"), now=NOW)
        self.assertEqual(lint_vault(vault)["status"], "pass")

    def test_own_folders_and_renames(self):
        vault = self.root / "v"
        plan = compose(
            roles=["creator"],
            folders=[("recipes", "Cooking recipes: ingredients and steps")],
            renames=[("concepts", "notes"), ("references", "sources")],
        )
        create_vault(vault, plan, now=NOW)
        self.assertGatePasses(vault)
        self.assertTrue((vault / "_meta" / "templates" / "recipes.md").is_file())
        page = (vault / "sources" / "karpathy-llm-wiki.md").read_text(encoding="utf-8")
        self.assertIn("\ncategory: sources\n", page)
        template = (vault / "_meta" / "templates" / "recipes.md").read_text(encoding="utf-8")
        self.assertIn("category: recipes", template)
        self.assertIn("Cooking recipes: ingredients and steps", template)


class CreateVaultContentTests(TempDirTestCase):
    def test_standard_files_demo_pages_by_role(self):
        vault = self.root / "v"
        create_vault(vault, compose(), now=NOW)
        expected = {
            "references/karpathy-llm-wiki.md": "references",
            "entities/llm-wiki-framework.md": "entities",
            "synthesis/why-agents-need-a-constitution.md": "synthesis",
            "concepts/llm-wiki-pattern.md": "concepts",
            "concepts/ingest-a-source.md": "concepts",
        }
        for relpath, category in expected.items():
            with self.subTest(page=relpath):
                text = (vault / relpath).read_text(encoding="utf-8")
                self.assertIn(f"\ncategory: {category}\n", text)

    def test_minimal_pages_keep_their_kind(self):
        vault = self.root / "v"
        create_vault(vault, compose("minimal"), now=NOW)
        text = (vault / "wiki" / "llm-wiki-framework.md").read_text(encoding="utf-8")
        self.assertIn("\ncategory: entities\n", text)
        index = (vault / "index.md").read_text(encoding="utf-8")
        for heading in ("## References", "## Entities", "## Synthesis", "## Concepts", "## Meta"):
            self.assertIn(heading, index)

    def test_agents_table_replaces_the_marker(self):
        vault = self.root / "v"
        create_vault(vault, compose(roles=["team"]), now=NOW)
        agents = (vault / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn(TABLE_MARKER, agents)
        self.assertIn("| `meetings/` |", agents)

    def test_bookkeeping_is_stamped_in_utc(self):
        vault = self.root / "v"
        create_vault(vault, compose(roles=["personal"]), now=NOW)
        log = (vault / "log.md").read_text(encoding="utf-8")
        self.assertIn("- [2026-11-02T09:30:00Z] INIT agent=llm-wiki", log)
        self.assertIn("pack=standard roles=personal", log)
        self.assertIn("categories=journal,references,entities,synthesis,concepts demo=yes", log)
        self.assertIn("SEED agent=llm-wiki pages_created=5", log)
        for name in ("index.md", "log.md", "hot.md", "AGENTS.md"):
            text = (vault / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"__[A-Z]+__", name)  # every init token was filled
        for name in ("index.md", "log.md", "hot.md"):
            self.assertIn("created: 2026-11-02", (vault / name).read_text(encoding="utf-8"))
        for path in (vault / "_meta" / "templates").glob("*.md"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"__[A-Z]+__", path.name)

    def test_empty_folders_keep_a_gitkeep(self):
        vault = self.root / "v"
        create_vault(vault, compose(roles=["learner"]), demo=False, now=NOW)
        self.assertTrue((vault / "courses" / ".gitkeep").is_file())
        self.assertTrue((vault / "concepts" / ".gitkeep").is_file())

    def test_no_demo_means_no_demo_links(self):
        vault = self.root / "v"
        create_vault(vault, compose(), demo=False, now=NOW)
        hot = (vault / "hot.md").read_text(encoding="utf-8")
        self.assertNotIn("[[llm-wiki-pattern]]", hot)
        self.assertIn("No pages yet", (vault / "index.md").read_text(encoding="utf-8"))
        self.assertNotIn("SEED", (vault / "log.md").read_text(encoding="utf-8"))

    def test_trimmed_base(self):
        vault = self.root / "v"
        create_vault(vault, compose(), now=NOW)
        for absent in ("docs", "_staging", "_archives", "_meta/trust-ledger.md", "_meta/manual.md", "_meta/hooks"):
            with self.subTest(absent=absent):
                self.assertFalse((vault / absent).exists())
        for present in ("AGENTS.md", "CLAUDE.md", "README.md", ".manifest.json", "_inbox", "_meta/taxonomy.md"):
            with self.subTest(present=present):
                self.assertTrue((vault / present).exists())

    def test_backup_hook_is_opt_in_and_lf(self):
        vault = self.root / "v"
        create_vault(vault, compose(), backup_hook=True, now=NOW)
        hook = (vault / "_meta" / "hooks" / "post-commit").read_bytes()
        self.assertTrue(hook.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r\n", hook)
        self.assertTrue((vault / ".gitattributes").is_file())
        if os.name == "posix":
            self.assertTrue(os.access(vault / "_meta" / "hooks" / "post-commit", os.X_OK))

    def test_written_files_use_lf(self):
        vault = self.root / "v"
        create_vault(vault, compose(), now=NOW)
        for path in [vault / "AGENTS.md", vault / "README.md", vault / "_meta" / "templates" / "concept.md"]:
            with self.subTest(file=path.name):
                self.assertNotIn(b"\r\n", path.read_bytes())


class TargetTests(TempDirTestCase):
    def test_refuses_a_non_empty_folder_and_leaves_it_alone(self):
        vault = self.root / "v"
        vault.mkdir()
        (vault / "notes.md").write_text("mine", encoding="utf-8")
        with self.assertRaises(ScaffoldError):
            create_vault(vault, compose(), now=NOW)
        self.assertEqual([p.name for p in vault.iterdir()], ["notes.md"])

    def test_refuses_a_file(self):
        path = self.root / "v"
        path.write_text("x", encoding="utf-8")
        with self.assertRaises(ScaffoldError):
            create_vault(path, compose(), now=NOW)

    def test_fills_an_existing_empty_folder(self):
        vault = self.root / "v"
        vault.mkdir()
        create_vault(vault, compose(), now=NOW)
        self.assertTrue((vault / "AGENTS.md").is_file())

    def test_creates_missing_parents_and_leaves_no_temporary_folder(self):
        vault = self.root / "a" / "b" / "v"
        create_vault(vault, compose(), now=NOW)
        self.assertEqual([p.name for p in vault.parent.iterdir()], ["v"])

    def test_failure_leaves_nothing_behind(self):
        vault = self.root / "v"
        plan = compose()
        broken = plan.rows[0].__class__(**{**plan.rows[0].__dict__, "template": "no-such-template"})
        plan = plan.__class__(**{**plan.__dict__, "rows": (broken,) + plan.rows[1:]})
        with self.assertRaises(FileNotFoundError):
            create_vault(vault, plan, now=NOW)
        self.assertEqual(list(self.root.iterdir()), [])


class PreviewTests(unittest.TestCase):
    def test_preview_shows_folders_and_the_table(self):
        text = render_preview(Path("my-wiki"), compose(roles=["creator"]), demo=False, backup_hook=True)
        self.assertTrue(text.startswith("my-wiki/\n"))
        self.assertIn("├── ideas/", text)
        self.assertIn("└── concepts/", text)
        self.assertIn("hooks/post-commit", text)
        self.assertIn("No demo pages.", text)
        self.assertIn("| `outputs/` |", text)

    def test_next_steps_mention_role_suggestions(self):
        plan = compose(roles=["team", "indie-hacker"])
        summary = {"path": "/x/v", "demo_pages": [], "backup_hook": True}
        text = next_steps(summary, plan)
        self.assertIn("WIKI_STAGED_WRITES", text)
        self.assertIn("process my Claude history", text)
        self.assertIn("core.hooksPath", text)
        self.assertNotIn("llm-wiki setup", next_steps(summary, plan, from_setup=True))


def scripted(*answers: str):
    """An `ask` that replays answers, then raises EOFError like a closed stdin."""
    queue = list(answers)

    def ask(prompt: str) -> str:
        if not queue:
            raise EOFError
        return queue.pop(0)

    return ask


class InterviewTests(unittest.TestCase):
    def run_interview(self, *answers: str):
        said: list[str] = []
        choices = interview(scripted(*answers), said.append, Path("my-wiki"))
        return choices, "\n".join(said)

    def test_enter_everywhere_gives_the_standard_pack(self):
        choices, _ = self.run_interview("", "", "", "", "", "", "")
        self.assertEqual(choices.plan.folders, ("references", "entities", "synthesis", "concepts"))
        self.assertTrue(choices.demo)
        self.assertFalse(choices.backup_hook)

    def test_roles_own_folder_and_rename(self):
        choices, _ = self.run_interview(
            "1",            # standard
            "3, creator",   # indie hacker + content creator
            "recipes=Cooking recipes",
            "",             # no more folders
            "concepts=notes",
            "",             # no more renames
            "n",            # no demo pages
            "y",            # backup hook
            "",             # create
        )
        self.assertEqual(choices.plan.roles, ("indie-hacker", "creator"))
        self.assertEqual(choices.plan.custom, ("recipes",))
        self.assertEqual(choices.plan.folders[-1], "notes")
        self.assertFalse(choices.demo)
        self.assertTrue(choices.backup_hook)

    def test_minimal_skips_the_role_questions(self):
        choices, said = self.run_interview("2", "", "", "", "")
        self.assertEqual(choices.plan.folders, ("wiki",))
        self.assertNotIn("What will you use it for?", said)

    def test_bad_answers_are_asked_again(self):
        choices, said = self.run_interview(
            "9", "1",               # out of range, then standard
            "wizard", "6",          # unknown role, then personal
            "Bad Name=x", "",       # invalid folder is refused
            "skills=how-to", "",    # renaming a missing folder is refused
            "", "", "",
        )
        self.assertEqual(choices.plan.roles, ("personal",))
        self.assertEqual(choices.plan.custom, ())
        self.assertIn("Pick a number", said)
        self.assertIn("Not a choice: wizard", said)
        self.assertIn("lowercase", said)
        self.assertIn("no such folder", said)

    def test_declining_at_the_end_cancels(self):
        choices, _ = self.run_interview("", "", "", "", "", "", "n")
        self.assertIsNone(choices)

    def test_closed_input_cancels(self):
        choices, _ = self.run_interview("1")
        self.assertIsNone(choices)


class SetupHandoffTests(TempDirTestCase):
    """`llm-wiki setup` offers the interview when the vault folder is new."""

    def offer(self, target: Path, *answers: str, tty: bool = True) -> tuple[dict, str]:
        from unittest import mock

        from llm_wiki.cli import _offer_new_vault

        out = io.StringIO()
        with mock.patch("sys.stdin") as stdin, mock.patch("builtins.input", scripted(*answers)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            stdin.isatty.return_value = tty
            extra = _offer_new_vault(str(target))
        return extra, out.getvalue()

    def test_existing_vault_is_left_alone(self):
        (self.root / "AGENTS.md").write_text("x", encoding="utf-8")
        extra, out = self.offer(self.root)
        self.assertEqual((extra, out), ({}, ""))

    def test_without_a_terminal_it_only_points_at_init(self):
        extra, out = self.offer(self.root / "v", tty=False)
        self.assertEqual(extra, {})
        self.assertIn("llm-wiki init", out)
        self.assertFalse((self.root / "v").exists())

    def test_declining_creates_nothing(self):
        extra, _ = self.offer(self.root / "v", "n")
        self.assertEqual(extra, {})
        self.assertFalse((self.root / "v").exists())

    def test_team_vault_defaults_to_staged_writes(self):
        vault = self.root / "v"
        extra, out = self.offer(
            vault,
            "",          # create it now
            "1", "team", "", "", "n", "", "",  # standard + team, no demo, no hook, create
            "",          # staged writes: take the team default
        )
        self.assertEqual(extra, {"WIKI_STAGED_WRITES": "true"})
        self.assertIn("Vault created", out)
        self.assertNotIn("llm-wiki setup --vault", out)  # setup is already running
        self.assertEqual(load_layout(vault).categories[0].folder, "meetings")

    def test_staged_writes_default_off_otherwise(self):
        extra, _ = self.offer(self.root / "v", "y", "2", "", "", "", "", "")
        self.assertEqual(extra, {"WIKI_STAGED_WRITES": "false"})


class InitCommandTests(TempDirTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_options_create_the_vault(self):
        vault = self.root / "v"
        code, out, _ = self.run_cli(
            "init", str(vault), "--role", "researcher", "--folder", "recipes=Cooking recipes", "--no-demo"
        )
        self.assertEqual(code, 0)
        self.assertIn("Vault created", out)
        self.assertEqual(load_layout(vault).categories[0].folder, "questions")

    def test_yes_without_options_creates_standard(self):
        vault = self.root / "v"
        code, _, _ = self.run_cli("init", str(vault), "--yes")
        self.assertEqual(code, 0)
        self.assertEqual([c.folder for c in load_layout(vault).categories], ["references", "entities", "synthesis", "concepts"])

    def test_dry_run_writes_nothing(self):
        vault = self.root / "v"
        code, out, _ = self.run_cli("init", str(vault), "--pack", "minimal", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("└── wiki/", out)
        self.assertFalse(vault.exists())

    def test_bad_choices_are_reported(self):
        code, _, err = self.run_cli("init", str(self.root / "v"), "--pack", "minimal", "--role", "team")
        self.assertEqual(code, 1)
        self.assertIn("single folder", err)

    def test_malformed_folder_option(self):
        code, _, err = self.run_cli("init", str(self.root / "v"), "--folder", "recipes")
        self.assertEqual(code, 1)
        self.assertIn("name=what it holds", err)

    def test_non_empty_target_is_refused(self):
        (self.root / "x.md").write_text("x", encoding="utf-8")
        code, _, err = self.run_cli("init", str(self.root), "--yes")
        self.assertEqual(code, 1)
        self.assertIn("not empty", err)

    def test_presets_json(self):
        code, out, _ = self.run_cli("presets", "--json")
        self.assertEqual(code, 0)
        self.assertIn('"default_pack": "standard"', out)


if __name__ == "__main__":
    unittest.main()
