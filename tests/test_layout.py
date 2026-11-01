"""Tests for reading a vault's page folders from the CATEGORIES table.

Stdlib unittest only — the repo has no runtime dependencies and the test
suite keeps it that way. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llm_wiki.layout import (
    LEGACY_LAYOUT,
    ROLES,
    Category,
    Layout,
    LayoutError,
    load_layout,
    parse_categories,
    render_table,
    validate,
)

TABLE = """\
| Folder | Holds | Role |
|---|---|---|
| `references/` | One page per ingested source | reference |
| `ideas/` | Content ideas |  |
| `notes/` | Everything else | concept |
"""


def agents(table: str = TABLE, before: str = "", after: str = "## OPERATIONS\n\nStuff.\n") -> str:
    return (
        "---\ntitle: AGENTS\n---\n\n# AGENTS.md\n\n## FOLDERS\n\n"
        "| Folder | Contents | Agent access |\n|---|---|---|\n| `_inbox/` | Sources | Read-only |\n\n"
        f"## CATEGORIES\n\n{before}{table}\n{after}"
    )


class ParseCategoriesTests(unittest.TestCase):
    def test_reads_rows_in_order(self):
        categories = parse_categories(agents())
        self.assertEqual(
            categories,
            (
                Category("references", "One page per ingested source", "reference"),
                Category("ideas", "Content ideas", None),
                Category("notes", "Everything else", "concept"),
            ),
        )

    def test_no_heading_means_no_table(self):
        self.assertIsNone(parse_categories("# AGENTS.md\n\n## FOLDERS\n\n| a | b |\n|---|---|\n"))

    def test_skips_the_folders_table_and_preamble_text(self):
        categories = parse_categories(agents(before="Wiki pages live only here.\n\n"))
        self.assertEqual([c.folder for c in categories], ["references", "ideas", "notes"])

    def test_heading_inside_a_code_fence_is_ignored(self):
        text = "# AGENTS.md\n\n```\n## CATEGORIES\n| Folder | Holds | Role |\n```\n"
        self.assertIsNone(parse_categories(text))

    def test_columns_are_found_by_name_and_extra_columns_ignored(self):
        table = (
            "| **Role** | Template | Folder | Holds |\n|:---|---|---|---:|\n"
            "| concept | note | notes | Everything |\n"
        )
        self.assertEqual(parse_categories(agents(table)), (Category("notes", "Everything", "concept"),))

    def test_backticks_and_trailing_slash_are_optional(self):
        table = "| Folder | Holds | Role |\n|---|---|---|\n| notes | Everything | concept |\n"
        self.assertEqual(parse_categories(agents(table))[0].folder, "notes")

    def test_dash_and_empty_mean_no_role(self):
        for cell in ("", "-", "—", "–"):
            with self.subTest(cell=cell):
                table = f"| Folder | Holds | Role |\n|---|---|---|\n| `a/` | A | {cell} |\n| `b/` | B | concept |\n"
                self.assertIsNone(parse_categories(agents(table))[0].role)

    def test_role_is_case_insensitive(self):
        table = "| Folder | Holds | Role |\n|---|---|---|\n| `notes/` | Everything | Concept |\n"
        self.assertEqual(parse_categories(agents(table))[0].role, "concept")

    def test_escaped_pipe_stays_inside_a_cell(self):
        table = "| Folder | Holds | Role |\n|---|---|---|\n| `notes/` | this \\| that | concept |\n"
        self.assertEqual(parse_categories(agents(table))[0].holds, "this | that")

    def test_crlf_line_endings(self):
        self.assertEqual(len(parse_categories(agents().replace("\n", "\r\n"))), 3)


class BrokenTableTests(unittest.TestCase):
    def assertProblem(self, text: str, fragment: str) -> None:
        with self.assertRaises(LayoutError) as caught:
            parse_categories(text)
        self.assertTrue(
            any(fragment in problem for problem in caught.exception.problems),
            f"{fragment!r} not in {caught.exception.problems}",
        )

    def test_heading_without_a_table(self):
        self.assertProblem(agents(table="Nothing here.\n"), "has no table")

    def test_table_after_the_next_heading_does_not_count(self):
        text = "## CATEGORIES\n\nSoon.\n\n## OPERATIONS\n\n" + TABLE
        self.assertProblem(text, "has no table")

    def test_two_sections(self):
        self.assertProblem(agents() + "\n## CATEGORIES\n\n" + TABLE, "more than one")

    def test_missing_separator_row(self):
        table = "| Folder | Holds | Role |\n| `notes/` | Everything | concept |\n"
        self.assertProblem(agents(table), "separator")

    def test_missing_role_column(self):
        table = "| Folder | Holds |\n|---|---|\n| `notes/` | Everything |\n"
        self.assertProblem(agents(table), "no Role column")

    def test_header_only(self):
        self.assertProblem(agents("| Folder | Holds | Role |\n|---|---|---|\n"), "no rows")

    def test_unescaped_pipe_in_a_cell(self):
        table = "| Folder | Holds | Role |\n|---|---|---|\n| `notes/` | this | that | concept |\n"
        self.assertProblem(agents(table), "4 cells")

    def test_every_problem_is_reported_at_once(self):
        table = (
            "| Folder | Holds | Role |\n|---|---|---|\n"
            "| `_notes/` | A | concept |\n| `Ideas/` | B | concept |\n| `x/` | C | wizard |\n"
        )
        with self.assertRaises(LayoutError) as caught:
            parse_categories(agents(table))
        self.assertEqual(len(caught.exception.problems), 4)


class ValidateTests(unittest.TestCase):
    def problems(self, *categories: Category) -> list[str]:
        return validate(categories)

    def test_valid(self):
        self.assertEqual(self.problems(Category("my-notes2", "x", "concept"), Category("a", "y")), [])

    def test_system_prefixes_are_rejected(self):
        for folder in ("_meta", ".obsidian"):
            with self.subTest(folder=folder):
                self.assertIn("system folders", self.problems(Category(folder, "x"))[0])

    def test_nested_folder_is_rejected(self):
        self.assertIn("single top-level", self.problems(Category("a/b", "x"))[0])

    def test_uppercase_and_spaces_are_rejected(self):
        for folder in ("Notes", "my notes"):
            with self.subTest(folder=folder):
                self.assertIn("lowercase", self.problems(Category(folder, "x"))[0])

    def test_duplicate_folder(self):
        self.assertIn("more than once", self.problems(Category("a", "x"), Category("a", "y"))[0])

    def test_duplicate_role(self):
        problems = self.problems(Category("a", "x", "concept"), Category("b", "y", "concept"))
        self.assertIn("claimed by both", problems[0])

    def test_unknown_role(self):
        self.assertIn("unknown role", self.problems(Category("a", "x", "wizard"))[0])

    def test_empty(self):
        self.assertIn("no rows", self.problems()[0])


class LayoutTests(unittest.TestCase):
    def test_folder_for_a_claimed_role(self):
        layout = Layout(parse_categories(agents()), source="AGENTS.md")
        self.assertEqual(layout.folder_for("reference"), "references")

    def test_unclaimed_role_falls_to_the_last_row(self):
        layout = Layout(parse_categories(agents()), source="AGENTS.md")
        for role in ("entity", "synthesis", "journal", "project", "procedure"):
            with self.subTest(role=role):
                self.assertEqual(layout.folder_for(role), "notes")

    def test_roles_covers_every_role(self):
        self.assertEqual(set(LEGACY_LAYOUT.roles()), set(ROLES))

    def test_unknown_role_lookup_is_an_error(self):
        with self.assertRaises(KeyError):
            LEGACY_LAYOUT.folder_for("wizard")

    def test_legacy_layout_is_the_original_seven(self):
        self.assertEqual(
            LEGACY_LAYOUT.folders,
            frozenset("concepts entities skills references synthesis journal projects".split()),
        )
        self.assertEqual(LEGACY_LAYOUT.catch_all.folder, "concepts")
        self.assertEqual(validate(LEGACY_LAYOUT.categories), [])

    def test_render_table_round_trips(self):
        categories = (
            Category("ideas", "Angles | hooks", None),
            Category("notes", "Everything else", "concept"),
        )
        self.assertEqual(parse_categories(agents(render_table(categories) + "\n")), categories)

    def test_to_dict(self):
        data = Layout(parse_categories(agents()), source="AGENTS.md").to_dict()
        self.assertEqual(data["catch_all"], "notes")
        self.assertEqual(data["roles"]["reference"], "references")
        self.assertEqual(data["categories"][1], {"folder": "ideas", "holds": "Content ideas", "role": None})


class LoadLayoutTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_no_agents_file_keeps_the_original_layout(self):
        self.assertIs(load_layout(self.vault), LEGACY_LAYOUT)

    def test_agents_file_without_table_keeps_the_original_layout(self):
        (self.vault / "AGENTS.md").write_text("# AGENTS.md\n\nLaws.\n", encoding="utf-8")
        self.assertIs(load_layout(self.vault), LEGACY_LAYOUT)

    def test_reads_the_table(self):
        (self.vault / "AGENTS.md").write_text(agents(), encoding="utf-8")
        layout = load_layout(self.vault)
        self.assertEqual(layout.source, "AGENTS.md")
        self.assertEqual(layout.folders, frozenset({"references", "ideas", "notes"}))

    def test_byte_order_mark_is_tolerated(self):
        (self.vault / "AGENTS.md").write_text("﻿" + agents(), encoding="utf-8")
        self.assertEqual(load_layout(self.vault).source, "AGENTS.md")

    def test_broken_table_raises(self):
        (self.vault / "AGENTS.md").write_text(agents(table="nope\n"), encoding="utf-8")
        with self.assertRaises(LayoutError):
            load_layout(self.vault)


if __name__ == "__main__":
    unittest.main()
