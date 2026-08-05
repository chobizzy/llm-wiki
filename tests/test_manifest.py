"""Tests for scripts/manifest.py.

normalize rewrites the ingest ledger in place, so the failure mode is silent
data loss: a bad merge drops the pages_created list that lets a re-ingest find
what a source produced, or clobbers the top-level `projects` block. Both look
like success at the command line.

Stdlib unittest only. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

# scripts/ is not a package, so load the module by path.
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "manifest.py"
_spec = importlib.util.spec_from_file_location("manifest_script", _SCRIPT)
manifest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manifest)


class CanonicalTests(unittest.TestCase):
    def test_expands_user_and_absolutises(self) -> None:
        got = manifest.canonical("~/notes/a.md")
        self.assertTrue(os.path.isabs(got))
        self.assertNotIn("~", got)

    def test_already_canonical_is_stable(self) -> None:
        once = manifest.canonical("~/notes/a.md")
        self.assertEqual(once, manifest.canonical(once))


class EntryTimeTests(unittest.TestCase):
    def test_reads_either_spelling(self) -> None:
        self.assertEqual(
            manifest.entry_time({"ingested_at": "2026-01-01T00:00:00Z"}),
            "2026-01-01T00:00:00Z",
        )
        self.assertEqual(
            manifest.entry_time({"last_ingested": "2026-02-02T00:00:00Z"}),
            "2026-02-02T00:00:00Z",
        )

    def test_missing_timestamp_is_empty_not_error(self) -> None:
        self.assertEqual(manifest.entry_time({}), "")


class MergeTests(unittest.TestCase):
    def test_newest_entry_supplies_scalars(self) -> None:
        old = {"ingested_at": "2026-01-01T00:00:00Z", "content_hash": "old"}
        new = {"ingested_at": "2026-06-01T00:00:00Z", "content_hash": "new"}
        self.assertEqual(manifest.merge_entries([old, new])["content_hash"], "new")
        # Order of the input must not decide the winner.
        self.assertEqual(manifest.merge_entries([new, old])["content_hash"], "new")

    def test_newest_wins_across_different_spellings(self) -> None:
        old = {"last_ingested": "2026-01-01T00:00:00Z", "content_hash": "old"}
        new = {"ingested_at": "2026-06-01T00:00:00Z", "content_hash": "new"}
        self.assertEqual(manifest.merge_entries([old, new])["content_hash"], "new")

    def test_page_provenance_is_unioned_not_overwritten(self) -> None:
        """The older duplicate's pages must survive the merge.

        Losing them strands the link a re-ingest uses to find the pages a
        source produced, which is the whole reason the manifest exists.
        """
        old = {
            "ingested_at": "2026-01-01T00:00:00Z",
            "pages_created": ["concepts/a.md"],
        }
        new = {
            "ingested_at": "2026-06-01T00:00:00Z",
            "pages_created": ["concepts/b.md"],
            "pages_updated": ["entities/c.md"],
        }
        merged = manifest.merge_entries([old, new])
        self.assertEqual(merged["pages_created"], ["concepts/a.md", "concepts/b.md"])
        self.assertEqual(merged["pages_updated"], ["entities/c.md"])


class NormalizeSourcesTests(unittest.TestCase):
    def test_tilde_and_absolute_forms_collapse_to_one(self) -> None:
        absolute = manifest.canonical("~/.claude/projects/x.jsonl")
        sources = {
            "~/.claude/projects/x.jsonl": {
                "ingested_at": "2026-01-01T00:00:00Z",
                "pages_created": ["a.md"],
            },
            absolute: {
                "ingested_at": "2026-06-01T00:00:00Z",
                "pages_created": ["b.md"],
            },
        }
        result, collisions = manifest.normalize_sources(sources)
        self.assertEqual(list(result), [absolute])
        self.assertEqual(len(collisions), 1)
        self.assertEqual(result[absolute]["pages_created"], ["a.md", "b.md"])

    def test_is_idempotent(self) -> None:
        sources = {"~/notes/a.md": {"ingested_at": "2026-01-01T00:00:00Z"}}
        once, _ = manifest.normalize_sources(sources)
        twice, collisions = manifest.normalize_sources(once)
        self.assertEqual(once, twice)
        self.assertEqual(collisions, [])

    def test_distinct_sources_are_not_merged(self) -> None:
        sources = {
            manifest.canonical("~/a.md"): {"ingested_at": "2026-01-01T00:00:00Z"},
            manifest.canonical("~/b.md"): {"ingested_at": "2026-01-01T00:00:00Z"},
        }
        result, collisions = manifest.normalize_sources(sources)
        self.assertEqual(len(result), 2)
        self.assertEqual(collisions, [])


class ManifestIOTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_save_preserves_unrelated_top_level_keys(self) -> None:
        """version and projects must survive a normalize.

        normalize only owns `sources`; silently dropping the sibling blocks
        would destroy per-project ingest state that nothing else rebuilds.
        """
        original = {
            "version": 1,
            "last_updated": "2026-04-06T10:30:00Z",
            "sources": {"~/a.md": {"ingested_at": "2026-01-01T00:00:00Z"}},
            "projects": {"my-app": {"conversations_ingested": 5}},
        }
        (self.vault / ".manifest.json").write_text(json.dumps(original), encoding="utf-8")

        doc = manifest.load_manifest(self.vault)
        doc["sources"], _ = manifest.normalize_sources(doc["sources"])
        manifest.save_manifest(self.vault, doc)

        written = json.loads((self.vault / ".manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(written["version"], 1)
        self.assertEqual(written["projects"], {"my-app": {"conversations_ingested": 5}})
        self.assertEqual(list(written["sources"]), [manifest.canonical("~/a.md")])

    def test_missing_manifest_yields_empty_skeleton(self) -> None:
        self.assertEqual(manifest.load_manifest(self.vault), {"sources": {}})

    def test_corrupt_manifest_fails_loudly(self) -> None:
        (self.vault / ".manifest.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(SystemExit):
            manifest.load_manifest(self.vault)

    def test_save_leaves_no_temp_file(self) -> None:
        manifest.save_manifest(self.vault, {"sources": {}})
        leftovers = list(self.vault.glob("*.tmp"))
        self.assertEqual(leftovers, [])


class ClassifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.source = Path(self._tmp.name) / "note.md"
        self.source.write_text("hello", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_unseen_source_is_new(self) -> None:
        self.assertEqual(manifest.classify(self.source, None), "new")

    def test_matching_hash_is_unchanged(self) -> None:
        from llm_wiki.cache import compute_hash

        entry = {"content_hash": compute_hash(self.source)}
        self.assertEqual(manifest.classify(self.source, entry), "unchanged")

    def test_differing_hash_is_modified(self) -> None:
        entry = {"content_hash": "deadbeef"}
        self.assertEqual(manifest.classify(self.source, entry), "modified")

    def test_newer_mtime_without_hash_is_touched(self) -> None:
        """Old entries carry no hash, so mtime is the only signal available."""
        entry = {"ingested_at": "1999-01-01T00:00:00+00:00"}
        self.assertEqual(manifest.classify(self.source, entry), "touched")


if __name__ == "__main__":
    unittest.main()
