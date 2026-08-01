"""Tests for local PDF text extraction and its content-hash cache.

Stdlib unittest only. PyMuPDF is an optional dependency, so every test that
needs it skips cleanly when it is absent.
Run: python -m unittest discover tests -v
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm_wiki.pdf_extract import (
    MIN_TEXT_CHARS,
    extract_pdf,
    find_tessdata,
    quiet_native_stdout,
)

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

LONG_TEXT = "Distillation beats summarisation for wiki ingest."


def _write_pdf(path: Path, page_texts: list[str | None]) -> None:
    """Build a PDF where each entry is page text, or None for a blank page."""
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


@unittest.skipUnless(HAS_PYMUPDF, "PyMuPDF not installed")
class ExtractPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.cache = self.tmp / "cache"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _extract(self, page_texts: list[str | None], **kwargs) -> dict:
        pdf = self.tmp / "doc.pdf"
        _write_pdf(pdf, page_texts)
        return extract_pdf(pdf, cache_dir=self.cache, ocr=False, **kwargs)

    def test_text_pages_are_extracted_without_vision(self) -> None:
        report = self._extract([LONG_TEXT, LONG_TEXT])
        self.assertEqual(report["page_count"], 2)
        self.assertEqual(report["text_pages"], 2)
        self.assertEqual(report["needs_vision"], [])
        self.assertGreater(report["chars"], 0)

    def test_pages_without_text_are_reported_for_vision(self) -> None:
        report = self._extract([None, None, None])
        self.assertEqual(report["text_pages"], 0)
        self.assertEqual(report["needs_vision"], [1, 2, 3])
        self.assertEqual(report["chars"], 0)

    def test_mixed_document_flags_only_the_blank_pages(self) -> None:
        report = self._extract([LONG_TEXT, None, LONG_TEXT])
        self.assertEqual(report["text_pages"], 2)
        self.assertEqual(report["needs_vision"], [2])

    def test_page_below_min_text_chars_counts_as_needing_vision(self) -> None:
        self.assertLess(len("x" * (MIN_TEXT_CHARS - 1)), MIN_TEXT_CHARS)
        report = self._extract(["x" * (MIN_TEXT_CHARS - 1)])
        self.assertEqual(report["needs_vision"], [1])

    def test_ocr_disabled_is_recorded(self) -> None:
        report = self._extract([None])
        self.assertFalse(report["ocr_available"])
        self.assertEqual(report["ocr_pages"], 0)

    def test_markdown_written_with_page_markers(self) -> None:
        report = self._extract([LONG_TEXT, None])
        markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
        self.assertIn("<!-- page 1 (text) -->", markdown)
        self.assertIn(LONG_TEXT, markdown)
        # The blank page contributes no body and so gets no marker.
        self.assertNotIn("<!-- page 2", markdown)

    def test_second_call_hits_the_cache(self) -> None:
        pdf = self.tmp / "doc.pdf"
        _write_pdf(pdf, [LONG_TEXT])
        first = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        self.assertFalse(first["cached"])
        second = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        self.assertTrue(second["cached"])
        self.assertEqual(first["content_hash"], second["content_hash"])

    def test_force_bypasses_the_cache(self) -> None:
        pdf = self.tmp / "doc.pdf"
        _write_pdf(pdf, [LONG_TEXT])
        extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        again = extract_pdf(pdf, cache_dir=self.cache, ocr=False, force=True)
        self.assertFalse(again["cached"])

    def test_changed_content_gets_a_new_cache_entry(self) -> None:
        pdf = self.tmp / "doc.pdf"
        _write_pdf(pdf, [LONG_TEXT])
        first = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        _write_pdf(pdf, [LONG_TEXT, LONG_TEXT])
        second = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        self.assertNotEqual(first["content_hash"], second["content_hash"])
        self.assertFalse(second["cached"])
        self.assertEqual(second["page_count"], 2)

    def test_corrupt_cache_entry_is_rebuilt(self) -> None:
        pdf = self.tmp / "doc.pdf"
        _write_pdf(pdf, [LONG_TEXT])
        first = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        (self.cache / f"{first['content_hash']}.json").write_text("{not json", encoding="utf-8")
        rebuilt = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        self.assertFalse(rebuilt["cached"])
        self.assertEqual(rebuilt["page_count"], 1)

    def test_report_sidecar_is_valid_json(self) -> None:
        pdf = self.tmp / "doc.pdf"
        _write_pdf(pdf, [LONG_TEXT])
        report = extract_pdf(pdf, cache_dir=self.cache, ocr=False)
        sidecar = json.loads(
            (self.cache / f"{report['content_hash']}.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sidecar["page_count"], 1)


class FindTessdataTests(unittest.TestCase):
    """Discovery has to survive a winget install, which never sets TESSDATA_PREFIX."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _tessdata_dir(self, name: str = "tessdata") -> Path:
        d = self.tmp / name
        d.mkdir()
        (d / "eng.traineddata").write_bytes(b"stub")
        return d

    def test_env_var_is_used_when_it_points_at_a_real_tessdata_dir(self) -> None:
        d = self._tessdata_dir()
        with mock.patch.dict(os.environ, {"TESSDATA_PREFIX": str(d)}):
            self.assertEqual(find_tessdata(), str(d))

    def test_env_var_pointing_at_an_empty_dir_is_rejected(self) -> None:
        empty = self.tmp / "empty"
        empty.mkdir()
        with mock.patch.dict(os.environ, {"TESSDATA_PREFIX": str(empty)}):
            with mock.patch("llm_wiki.pdf_extract.TESSDATA_CANDIDATES", ()):
                self.assertIsNone(find_tessdata())

    def test_env_var_pointing_at_a_missing_dir_is_rejected(self) -> None:
        with mock.patch.dict(os.environ, {"TESSDATA_PREFIX": str(self.tmp / "nope")}):
            with mock.patch("llm_wiki.pdf_extract.TESSDATA_CANDIDATES", ()):
                self.assertIsNone(find_tessdata())

    def test_standard_install_path_found_without_the_env_var(self) -> None:
        d = self._tessdata_dir()
        env = {k: v for k, v in os.environ.items() if k != "TESSDATA_PREFIX"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("llm_wiki.pdf_extract.TESSDATA_CANDIDATES", (str(d),)):
                self.assertEqual(find_tessdata(), str(d))

    def test_returns_none_when_nothing_is_installed(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "TESSDATA_PREFIX"}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("llm_wiki.pdf_extract.TESSDATA_CANDIDATES", (str(self.tmp / "nope"),)):
                self.assertIsNone(find_tessdata())


class QuietNativeStdoutTests(unittest.TestCase):
    """Tesseract's fd-1 diagnostics must never land in the command's JSON."""

    def test_fd_writes_are_diverted_then_stdout_is_restored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            capture = Path(tmp) / "stdout.txt"
            with open(capture, "w", encoding="utf-8") as fh:
                saved = os.dup(1)
                os.dup2(fh.fileno(), 1)
                try:
                    with quiet_native_stdout():
                        os.write(1, b"NOISE\n")
                    os.write(1, b"JSON\n")
                finally:
                    os.dup2(saved, 1)
                    os.close(saved)
            written = capture.read_text(encoding="utf-8")
        self.assertNotIn("NOISE", written)
        self.assertIn("JSON", written)


class MissingSourceTests(unittest.TestCase):
    def test_missing_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                extract_pdf(Path(tmp) / "nope.pdf", cache_dir=Path(tmp) / "cache")


if __name__ == "__main__":
    unittest.main()
