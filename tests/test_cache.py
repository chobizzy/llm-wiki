"""Tests for the manifest schema written by cache-update.

DONE criterion 2 of the vault constitution requires absolute path keys and a
populated pages_created / pages_updated split, so those are gate behaviour
rather than nice-to-haves.

Stdlib unittest only. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from llm_wiki.cache import check_sources, update_source


class UpdateSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.source = self.vault / "_inbox" / "note.md"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("a source document", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _manifest(self) -> dict:
        return json.loads((self.vault / ".manifest.json").read_text(encoding="utf-8"))

    def _entry(self) -> dict:
        return self._manifest()["sources"][os.path.abspath(self.source)]

    def test_records_created_and_updated_separately(self) -> None:
        update_source(
            self.vault,
            self.source,
            pages_created=["concepts/new.md"],
            pages_updated=["entities/existing.md"],
        )
        entry = self._entry()
        self.assertEqual(entry["pages_created"], ["concepts/new.md"])
        self.assertEqual(entry["pages_updated"], ["entities/existing.md"])

    def test_key_is_an_absolute_path(self) -> None:
        update_source(self.vault, self.source, pages_created=[])
        key = next(iter(self._manifest()["sources"]))
        self.assertTrue(os.path.isabs(key))
        self.assertEqual(key, os.path.abspath(self.source))

    def test_hash_and_timestamp_are_recorded(self) -> None:
        returned = update_source(self.vault, self.source, pages_created=[])
        entry = self._entry()
        self.assertEqual(entry["content_hash"], returned)
        self.assertEqual(len(returned), 64)
        self.assertTrue(entry["last_ingested"].endswith("+00:00"))

    def test_legacy_pages_produced_entry_is_migrated(self) -> None:
        key = os.path.abspath(self.source)
        (self.vault / ".manifest.json").write_text(
            json.dumps({
                "sources": {
                    key: {
                        "content_hash": "stale",
                        "last_ingested": "2026-01-01T00:00:00+00:00",
                        "pages_produced": ["concepts/old.md"],
                    }
                }
            }),
            encoding="utf-8",
        )
        update_source(self.vault, self.source, pages_created=["concepts/new.md"])
        entry = self._entry()
        self.assertNotIn("pages_produced", entry)
        self.assertEqual(entry["pages_created"], ["concepts/new.md"])

    def test_relative_key_is_not_duplicated_on_rewrite(self) -> None:
        rel_key = str(self.source)
        (self.vault / ".manifest.json").write_text(
            json.dumps({"sources": {rel_key: {"content_hash": "stale"}}}),
            encoding="utf-8",
        )
        update_source(self.vault, self.source, pages_created=[])
        self.assertEqual(len(self._manifest()["sources"]), 1)

    def test_other_top_level_manifest_keys_survive(self) -> None:
        (self.vault / ".manifest.json").write_text(
            json.dumps({"sources": {}, "hermes": {"sessions_scanned": 22}}),
            encoding="utf-8",
        )
        update_source(self.vault, self.source, pages_created=[])
        self.assertEqual(self._manifest()["hermes"]["sessions_scanned"], 22)

    def test_omitting_page_lists_leaves_existing_ones_intact(self) -> None:
        update_source(self.vault, self.source, pages_created=["concepts/a.md"])
        update_source(self.vault, self.source)
        self.assertEqual(self._entry()["pages_created"], ["concepts/a.md"])

    def test_recorded_source_reads_back_as_unchanged(self) -> None:
        update_source(self.vault, self.source, pages_created=[])
        result = check_sources(self.vault, [self.source])
        self.assertEqual(result["unchanged"], [str(self.source)])
        self.assertEqual(result["new"], [])

    def test_edited_source_reads_back_as_modified(self) -> None:
        update_source(self.vault, self.source, pages_created=[])
        self.source.write_text("the document changed", encoding="utf-8")
        result = check_sources(self.vault, [self.source])
        self.assertEqual(result["modified"], [str(self.source)])


if __name__ == "__main__":
    unittest.main()
