"""Tests for scripts/manifest.py.

normalize rewrites the ingest ledger in place, so the failure mode is silent
data loss: a bad merge drops the pages_created list that lets a re-ingest find
what a source produced, or clobbers the top-level `projects` block. Both look
like success at the command line.

Stdlib unittest only. Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

from llm_wiki.cache import check_sources, compute_hash, update_source

# scripts/ is not a package, so load the module by path.
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "manifest.py"
_spec = importlib.util.spec_from_file_location("manifest_script", _SCRIPT)
manifest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manifest)


class CanonicalTests(unittest.TestCase):
    """canonical_key and entry_time are llm_wiki.cache's; covered in test_cache.

    These only pin that the script uses the shared helpers rather than its own.
    """

    def test_uses_the_shared_canonical_key(self) -> None:
        from llm_wiki.cache import canonical_key

        self.assertIs(manifest.canonical_key, canonical_key)

    def test_uses_the_shared_entry_time(self) -> None:
        from llm_wiki.cache import entry_time

        self.assertIs(manifest.entry_time, entry_time)


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
        absolute = manifest.canonical_key("~/.claude/projects/x.jsonl")
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
            manifest.canonical_key("~/a.md"): {"ingested_at": "2026-01-01T00:00:00Z"},
            manifest.canonical_key("~/b.md"): {"ingested_at": "2026-01-01T00:00:00Z"},
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
        manifest.write_manifest_doc(self.vault, doc)

        written = json.loads((self.vault / ".manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(written["version"], 1)
        self.assertEqual(written["projects"], {"my-app": {"conversations_ingested": 5}})
        self.assertEqual(list(written["sources"]), [manifest.canonical_key("~/a.md")])

    def test_missing_manifest_yields_empty_skeleton(self) -> None:
        self.assertEqual(manifest.load_manifest(self.vault), {"sources": {}})

    def test_corrupt_manifest_fails_loudly(self) -> None:
        (self.vault / ".manifest.json").write_text("{not json", encoding="utf-8")
        with self.assertRaises(SystemExit):
            manifest.load_manifest(self.vault)

    def test_save_leaves_no_temp_file(self) -> None:
        manifest.write_manifest_doc(self.vault, {"sources": {}})
        leftovers = list(self.vault.glob("*.tmp"))
        self.assertEqual(leftovers, [])


class DeltaTests(unittest.TestCase):
    """delta must stay a thin wrapper over cache.check_sources.

    The failure this guards is silent: if delta ever classifies on its own
    again, it can call a source unchanged that cache-check calls modified, and
    the ingest skips a file that really did change.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name) / "vault"
        self.vault.mkdir()
        self.sources_dir = Path(self._tmp.name) / "sources"
        self.sources_dir.mkdir()
        self.source = self.sources_dir / "note.md"
        self.source.write_text("hello", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _delta(self) -> dict:
        args = argparse.Namespace(
            vault=str(self.vault),
            scan=[str(self.sources_dir / "*.md")],
            skip=None,
            json=True,
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            manifest.cmd_delta(args)
        return json.loads(out.getvalue())

    def test_unrecorded_source_is_new(self) -> None:
        self.assertEqual(self._delta()["new"], [str(self.source)])

    def test_recorded_source_is_unchanged(self) -> None:
        update_source(self.vault, self.source, pages_created=[])
        got = self._delta()
        self.assertEqual(got["unchanged"], [str(self.source)])
        self.assertEqual(got["new"], [])

    def test_resolves_a_non_canonical_manifest_key(self) -> None:
        """The reason delta exists: an entry keyed in some other path form."""
        odd_key = str(self.sources_dir / "sub" / ".." / "note.md")
        (self.vault / ".manifest.json").write_text(
            json.dumps({"sources": {odd_key: {"content_hash": compute_hash(self.source)}}}),
            encoding="utf-8",
        )
        self.assertEqual(self._delta()["unchanged"], [str(self.source)])

    def test_gives_the_same_answer_as_cache_check(self) -> None:
        update_source(self.vault, self.source, pages_created=[])
        self.source.write_text("the document changed", encoding="utf-8")
        self.assertEqual(self._delta(), check_sources(self.vault, [self.source]))


if __name__ == "__main__":
    unittest.main()
