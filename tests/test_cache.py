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

from llm_wiki.cache import (
    ManifestError,
    canonical_key,
    check_sources,
    compute_hash,
    entry_time,
    update_source,
)


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
        self.assertTrue(entry["ingested_at"].endswith("+00:00"))

    def test_legacy_pages_produced_entry_is_migrated(self) -> None:
        key = os.path.abspath(self.source)
        (self.vault / ".manifest.json").write_text(
            json.dumps({
                "sources": {
                    key: {
                        "content_hash": "stale",
                        "ingested_at": "2026-01-01T00:00:00+00:00",
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

    def test_legacy_last_ingested_is_migrated_to_ingested_at(self) -> None:
        """One timestamp field, not two.

        Leaving `last_ingested` behind alongside `ingested_at` would give a
        reader two stamps for one ingest and no rule for which is authoritative.
        """
        (self.vault / ".manifest.json").write_text(
            json.dumps({
                "sources": {
                    os.path.abspath(self.source): {
                        "content_hash": "stale",
                        "last_ingested": "2026-01-01T00:00:00+00:00",
                    }
                }
            }),
            encoding="utf-8",
        )
        update_source(self.vault, self.source, pages_created=[])
        entry = self._entry()
        self.assertNotIn("last_ingested", entry)
        self.assertTrue(entry["ingested_at"].endswith("+00:00"))

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

    def test_write_leaves_no_temp_file_behind(self) -> None:
        """The write goes via <name>.tmp and renames; nothing should survive it."""
        update_source(self.vault, self.source, pages_created=[])
        self.assertEqual(list(self.vault.glob("*.tmp")), [])

    def test_every_spelling_of_the_path_collapses_to_one_entry(self) -> None:
        """A duplicate left behind is a stale entry a later check can read."""
        (self.vault / ".manifest.json").write_text(
            json.dumps({
                "sources": {
                    str(self.vault / "_inbox" / "sub" / ".." / "note.md"): {
                        "content_hash": "stale",
                        "ingested_at": "2026-01-01T00:00:00+00:00",
                    }
                }
            }),
            encoding="utf-8",
        )
        update_source(self.vault, self.source, pages_created=[])
        sources = self._manifest()["sources"]
        self.assertEqual(list(sources), [os.path.abspath(self.source)])


class DamagedManifestTests(unittest.TestCase):
    """A manifest that won't parse must stop the run, not read as empty.

    Reading it as empty is the worst kind of quiet: cache-check calls every
    source new and the vault gets fully re-ingested, then the next write
    replaces the damaged file with one holding nothing but `sources` — so the
    projects and stats blocks are gone and nothing ever reported a problem.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.source = self.vault / "note.md"
        self.source.write_text("a source document", encoding="utf-8")
        self.manifest = self.vault / ".manifest.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_check_sources_raises_instead_of_reporting_everything_new(self) -> None:
        self.manifest.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ManifestError):
            check_sources(self.vault, [self.source])

    def test_update_source_raises_and_leaves_the_file_alone(self) -> None:
        damaged = '{"sources": {"a.md": {}}, truncated'
        self.manifest.write_text(damaged, encoding="utf-8")
        with self.assertRaises(ManifestError):
            update_source(self.vault, self.source, pages_created=[])
        self.assertEqual(self.manifest.read_text(encoding="utf-8"), damaged)

    def test_non_object_manifest_raises(self) -> None:
        self.manifest.write_text('["not", "an", "object"]', encoding="utf-8")
        with self.assertRaises(ManifestError):
            check_sources(self.vault, [self.source])

    def test_non_object_sources_block_raises(self) -> None:
        self.manifest.write_text('{"sources": ["a.md"]}', encoding="utf-8")
        with self.assertRaises(ManifestError):
            check_sources(self.vault, [self.source])

    def test_absent_manifest_is_still_a_fresh_vault(self) -> None:
        """The one legitimately empty case — do not make this an error too."""
        self.assertEqual(check_sources(self.vault, [self.source])["new"],
                         [str(self.source)])


class EntryTimeTests(unittest.TestCase):
    def test_reads_either_spelling(self) -> None:
        self.assertEqual(
            entry_time({"ingested_at": "2026-01-01T00:00:00Z"}),
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(
            entry_time({"last_ingested": "2026-02-02T00:00:00Z"}),
            "2026-02-02T00:00:00Z",
        )

    def test_missing_timestamp_is_empty_not_error(self) -> None:
        self.assertEqual(entry_time({}), "")


class CanonicalKeyTests(unittest.TestCase):
    def test_expands_user_and_absolutises(self) -> None:
        got = canonical_key("~/notes/a.md")
        self.assertTrue(os.path.isabs(got))
        self.assertNotIn("~", got)

    def test_already_canonical_is_stable(self) -> None:
        once = canonical_key("~/notes/a.md")
        self.assertEqual(once, canonical_key(once))


class CheckSourcesSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)
        self.source = self.vault / "note.md"
        self.source.write_text("a source document", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_entry(self, key: str, entry: dict) -> None:
        (self.vault / ".manifest.json").write_text(
            json.dumps({"sources": {key: entry}}), encoding="utf-8"
        )

    def test_finds_an_entry_stored_under_a_non_canonical_key(self) -> None:
        """A manifest that mixes key forms must not read as a fresh vault.

        Missing the other form re-ingests a source already processed — the bug
        `scripts/manifest.py normalize` exists to repair.
        """
        self._write_entry(
            str(self.vault / "sub" / ".." / "note.md"),
            {"content_hash": compute_hash(self.source)},
        )
        result = check_sources(self.vault, [self.source])
        self.assertEqual(result["unchanged"], [str(self.source)])
        self.assertEqual(result["new"], [])

    def test_entry_without_a_hash_is_modified_not_unchanged(self) -> None:
        """Pre-hash entries carry no proof the content is the same.

        Calling them unchanged would skip a file that really did change; the
        re-ingest is the only answer that cannot be wrong, and it backfills
        the hash so the guess is never needed twice.
        """
        self._write_entry(
            str(self.source), {"ingested_at": "1999-01-01T00:00:00+00:00"}
        )
        result = check_sources(self.vault, [self.source])
        self.assertEqual(result["modified"], [str(self.source)])


if __name__ == "__main__":
    unittest.main()
