"""Tests for the doctor's required-files and git-tree checks.

Stdlib unittest only — the repo has no runtime dependencies and the test
suite keeps it that way. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from llm_wiki.cli import _check_git_tree, _check_layout, _check_required_files, _extra_required_files

CATEGORIES = """# AGENTS.md

## CATEGORIES

| Folder | Holds | Role |
|---|---|---|
| `references/` | One page per source | reference |
| `wiki/` | Everything else | concept |
"""


class CheckLayoutTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _agents(self, text: str) -> None:
        (self.vault / "AGENTS.md").write_text(text, encoding="utf-8")

    def test_vault_without_table_passes_on_the_original_layout(self):
        check = _check_layout(self.vault)
        self.assertEqual(check["name"], "vault-layout")
        self.assertEqual(check["status"], "pass")
        self.assertIn("original layout", check["detail"])

    def test_original_layout_does_not_require_its_folders(self):
        # Vaults made before the table often lack a few of the seven folders.
        self._agents("# AGENTS.md\n\nNo table here.\n")
        self.assertEqual(_check_layout(self.vault)["status"], "pass")

    def test_passes_when_every_declared_folder_exists(self):
        self._agents(CATEGORIES)
        (self.vault / "references").mkdir()
        (self.vault / "wiki").mkdir()
        check = _check_layout(self.vault)
        self.assertEqual(check["status"], "pass")
        self.assertIn("references/, wiki/", check["detail"])

    def test_warns_and_names_missing_folders(self):
        self._agents(CATEGORIES)
        (self.vault / "wiki").mkdir()
        check = _check_layout(self.vault)
        self.assertEqual(check["status"], "warn")
        self.assertIn("references/", check["detail"])
        self.assertNotIn("wiki/", check["detail"])

    def test_fails_on_a_broken_table(self):
        self._agents("# AGENTS.md\n\n## CATEGORIES\n\nNothing yet.\n")
        check = _check_layout(self.vault)
        self.assertEqual(check["status"], "fail")
        self.assertIn("has no table", check["detail"])


class ExtraRequiredFilesTests(unittest.TestCase):
    def test_returns_empty_list_when_key_absent(self):
        self.assertEqual(_extra_required_files({}), [])

    def test_splits_on_commas_and_strips_whitespace(self):
        config = {"WIKI_REQUIRED_FILES": "AGENTS.md, retrieval-ledger.md ,hot.md"}
        self.assertEqual(
            _extra_required_files(config),
            ["AGENTS.md", "retrieval-ledger.md", "hot.md"],
        )

    def test_ignores_empty_segments(self):
        config = {"WIKI_REQUIRED_FILES": ",AGENTS.md,,"}
        self.assertEqual(_extra_required_files(config), ["AGENTS.md"])


class CheckRequiredFilesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_returns_none_when_nothing_required(self):
        self.assertIsNone(_check_required_files(self.vault, []))

    def test_passes_when_all_required_files_exist(self):
        (self.vault / "AGENTS.md").write_text("x", encoding="utf-8")
        check = _check_required_files(self.vault, ["AGENTS.md"])
        self.assertEqual(check["name"], "required-files")
        self.assertEqual(check["status"], "pass")

    def test_fails_and_names_the_missing_files(self):
        (self.vault / "AGENTS.md").write_text("x", encoding="utf-8")
        check = _check_required_files(
            self.vault, ["AGENTS.md", "retrieval-ledger.md"]
        )
        self.assertEqual(check["status"], "fail")
        self.assertIn("retrieval-ledger.md", check["detail"])
        self.assertNotIn("AGENTS.md,", check["detail"])


def _git(vault: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(vault), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class CheckGitTreeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _init_repo(self) -> None:
        _git(self.vault, "init", "-q")
        _git(self.vault, "config", "user.email", "test@example.com")
        _git(self.vault, "config", "user.name", "test")

    def test_returns_none_for_non_git_vault(self):
        self.assertIsNone(_check_git_tree(self.vault))

    def test_passes_on_clean_tree(self):
        self._init_repo()
        (self.vault / "index.md").write_text("x", encoding="utf-8")
        _git(self.vault, "add", "-A")
        _git(self.vault, "commit", "-q", "-m", "init")
        check = _check_git_tree(self.vault)
        self.assertEqual(check["name"], "git-tree")
        self.assertEqual(check["status"], "pass")

    def test_warns_on_dirty_tree_with_count_and_law9_hint(self):
        self._init_repo()
        (self.vault / "index.md").write_text("x", encoding="utf-8")
        _git(self.vault, "add", "-A")
        _git(self.vault, "commit", "-q", "-m", "init")
        (self.vault / "index.md").write_text("changed", encoding="utf-8")
        (self.vault / "new-page.md").write_text("y", encoding="utf-8")
        check = _check_git_tree(self.vault)
        self.assertEqual(check["status"], "warn")
        self.assertIn("2 uncommitted change(s)", check["detail"])
        self.assertIn("law 9", check["hint"])

    def test_dirty_detail_includes_last_logged_operation(self):
        self._init_repo()
        (self.vault / "log.md").write_text(
            "# Wiki Log\n\n"
            "- [2026-01-01T00:00:00Z] INIT agent=claude-code\n"
            "- [2026-01-02T00:00:00Z] LINT agent=hermes issues_found=0\n",
            encoding="utf-8",
        )
        _git(self.vault, "add", "-A")
        _git(self.vault, "commit", "-q", "-m", "init")
        (self.vault / "page.md").write_text("dirty", encoding="utf-8")
        check = _check_git_tree(self.vault)
        self.assertEqual(check["status"], "warn")
        self.assertIn("LINT agent=hermes", check["detail"])


if __name__ == "__main__":
    unittest.main()
