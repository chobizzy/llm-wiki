"""Tests for the lint check on lifecycle frontmatter states.

Stdlib unittest only — the repo has no runtime dependencies and the test
suite keeps it that way. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llm_wiki.lint import VALID_LIFECYCLE, lint_vault

PAGE = """---
title: {title}
category: concepts
tags: [x]
sources: [system]
summary: A page.
{lifecycle_line}created: 2026-01-01
updated: 2026-01-01
---

# {title}

Body text linking [[other]].
"""

OTHER = """---
title: Other
category: concepts
tags: [x]
sources: [system]
summary: The link target, so nothing here is a broken link.
lifecycle: draft
created: 2026-01-01
updated: 2026-01-01
---

# Other

Points back at [[page]].
"""


class InvalidLifecycleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.vault / "other.md").write_text(OTHER, encoding="utf-8")

    def _write(self, lifecycle: str | None, name: str = "page") -> None:
        line = "" if lifecycle is None else f"lifecycle: {lifecycle}\n"
        (self.vault / f"{name}.md").write_text(
            PAGE.format(title=name.title(), lifecycle_line=line), encoding="utf-8"
        )

    def _findings(self) -> list[dict[str, str]]:
        return lint_vault(self.vault)["findings"]["invalid_lifecycle"]

    def test_every_documented_state_is_accepted(self):
        for state in VALID_LIFECYCLE:
            with self.subTest(state=state):
                self._write(state)
                self.assertEqual(self._findings(), [])

    def test_flags_an_invented_state_and_reports_the_value(self):
        self._write("evergreen")
        self.assertEqual(
            self._findings(), [{"page": "page.md", "value": "evergreen"}]
        )

    def test_absent_lifecycle_is_not_flagged(self):
        # Missing lifecycle is a missing_frontmatter concern, not this check's.
        self._write(None)
        self.assertEqual(self._findings(), [])

    def test_quoted_value_is_unwrapped_before_comparison(self):
        self._write('"draft"')
        self.assertEqual(self._findings(), [])

    def test_case_variant_is_rejected(self):
        self._write("Draft")
        self.assertEqual(self._findings(), [{"page": "page.md", "value": "Draft"}])

    def test_invalid_lifecycle_fails_the_gate(self):
        self._write("evergreen")
        report = lint_vault(self.vault)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["stats"]["findings"]["invalid_lifecycle"], 1)

    def test_valid_lifecycle_alone_does_not_fail_the_gate(self):
        self._write("draft")
        report = lint_vault(self.vault)
        self.assertNotEqual(report["status"], "fail")

    def test_reports_every_offending_page(self):
        self._write("evergreen", name="page")
        self._write("perennial", name="second")
        self.assertEqual(
            sorted(self._findings(), key=lambda f: f["page"]),
            [
                {"page": "page.md", "value": "evergreen"},
                {"page": "second.md", "value": "perennial"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
