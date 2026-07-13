"""llm-wiki: self-owned LLM wiki skills + helper CLI for an Obsidian knowledge vault.

The product is the markdown skill content under ``skills/`` at the repo root.
This module is the helper CLI — graph analysis, ingest caching, batch planning,
AST extraction, linting — plus the installer that links the skills into AI
coding agents. See ``cli.py``.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("llm-wiki")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+dev"

__all__ = ["__version__"]
