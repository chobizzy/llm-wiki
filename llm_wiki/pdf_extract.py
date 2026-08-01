"""Local PDF text extraction with a content-hash cache.

Pulls the text layer out of a PDF locally so wiki-ingest never spends a vision
read on a page whose text was already machine-readable. Pages with no text
layer are OCR'd when Tesseract is available; whatever is left is reported as
`needs_vision` so the skill vision-reads exactly those pages and no others.

Results are cached by source content hash, so re-ingesting an unchanged PDF
costs nothing.

Requires PyMuPDF (`pip install pymupdf`) — imported lazily so the rest of the
CLI stays stdlib-only. OCR additionally requires Tesseract on the system.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from llm_wiki.cache import sha256_file

# A page needs this many non-whitespace characters to count as having a text
# layer. Scanned pages often carry a stray artefact or two.
MIN_TEXT_CHARS = 20

DEFAULT_OCR_DPI = 300
DEFAULT_OCR_LANGUAGE = "eng"

# Standard tessdata locations, searched when TESSDATA_PREFIX is unset. The
# Windows installers (winget, choco) do not set that variable, so without this
# list OCR stays silently unavailable on a machine that has Tesseract.
TESSDATA_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tessdata",
    r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
    "/opt/homebrew/share/tessdata",
    "/usr/local/share/tessdata",
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tessdata",
)


def _is_tessdata_dir(path: Path) -> bool:
    """A usable tessdata dir exists and holds at least one language model."""
    return path.is_dir() and any(path.glob("*.traineddata"))


def find_tessdata() -> str | None:
    """Locate a tessdata directory, or None when OCR is unavailable."""
    env = os.environ.get("TESSDATA_PREFIX")
    if env and _is_tessdata_dir(Path(env)):
        return env
    for candidate in TESSDATA_CANDIDATES:
        if _is_tessdata_dir(Path(candidate)):
            return candidate
    return None


def default_cache_dir() -> Path:
    """Cache lives outside the vault — the vault holds wiki pages, not build artefacts."""
    return Path.home() / ".llm-wiki" / "cache" / "pdf"


def _import_fitz():
    try:
        import fitz  # noqa: PLC0415 — lazy so the CLI stays stdlib-only
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for pdf-extract: pip install pymupdf"
        ) from exc
    return fitz


@contextlib.contextmanager
def quiet_native_stdout():
    """Route file-descriptor-level writes to stderr for the duration of the block.

    Tesseract reports unreadable regions ("Image too small to scale!!") on
    fd 1 from C, where `contextlib.redirect_stdout` cannot reach it. Left
    alone it interleaves with this command's JSON and breaks every consumer
    that pipes stdout. Diagnostics still reach the user, just on stderr.
    """
    sys.stdout.flush()
    saved = os.dup(1)
    try:
        os.dup2(2, 1)
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)


def _page_text(page) -> str:
    return (page.get_text() or "").strip()


def _ocr_page_text(page, *, dpi: int, language: str, tessdata: str) -> str:
    """OCR a whole page. Returns "" if this page's OCR fails."""
    try:
        textpage = page.get_textpage_ocr(
            flags=3, language=language, dpi=dpi, full=True, tessdata=tessdata
        )
        return (page.get_text("text", textpage=textpage) or "").strip()
    except Exception:
        # One unreadable page must not sink the whole document — the page
        # falls through to needs_vision, which is the correct fallback.
        return ""


def _render_markdown(source: Path, pages: list[dict]) -> str:
    lines = [f"<!-- extracted from {source.name} -->", ""]
    for page in pages:
        if not page["text"]:
            continue
        lines.append(f"<!-- page {page['number']} ({page['method']}) -->")
        lines.append(page["text"])
        lines.append("")
    return "\n".join(lines)


def extract_pdf(
    source: Path,
    *,
    cache_dir: Path | None = None,
    ocr: bool = True,
    dpi: int = DEFAULT_OCR_DPI,
    language: str = DEFAULT_OCR_LANGUAGE,
    tessdata: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Extract text from *source*, caching by content hash.

    Returns a report dict; the extracted markdown is written to the cache dir
    and its path returned as `markdown_path`.
    """
    if not source.is_file():
        raise FileNotFoundError(f"not a file: {source}")

    cache_dir = cache_dir or default_cache_dir()
    content_hash = sha256_file(source)
    markdown_path = cache_dir / f"{content_hash}.md"
    report_path = cache_dir / f"{content_hash}.json"

    if not force and report_path.is_file() and markdown_path.is_file():
        try:
            cached = json.loads(report_path.read_text(encoding="utf-8"))
            return {**cached, "cached": True}
        except (json.JSONDecodeError, OSError):
            pass  # unreadable cache entry — fall through and rebuild it

    fitz = _import_fitz()
    tessdata = tessdata or find_tessdata()
    use_ocr = ocr and tessdata is not None

    pages: list[dict] = []
    with fitz.open(source) as doc, quiet_native_stdout():
        for index, page in enumerate(doc, start=1):
            text = _page_text(page)
            method = "text"
            if len(text) < MIN_TEXT_CHARS:
                text = (
                    _ocr_page_text(page, dpi=dpi, language=language, tessdata=tessdata)
                    if use_ocr
                    else ""
                )
                method = "ocr" if text else "none"
            pages.append({"number": index, "text": text, "method": method})

    report = {
        "source": str(source),
        "content_hash": content_hash,
        "page_count": len(pages),
        "text_pages": sum(1 for p in pages if p["method"] == "text"),
        "ocr_pages": sum(1 for p in pages if p["method"] == "ocr"),
        "needs_vision": [p["number"] for p in pages if p["method"] == "none"],
        "chars": sum(len(p["text"]) for p in pages),
        "ocr_available": use_ocr,
        "tessdata": tessdata,
        "markdown_path": str(markdown_path),
        "cached": False,
    }

    cache_dir.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(_render_markdown(source, pages), encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
