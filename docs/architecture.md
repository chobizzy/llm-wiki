---
title: Architecture
category: meta
tags: [meta, knowledge-management]
sources: [owner]
summary: The three-layer design of this vault — immutable sources, compiled pages, and the bookkeeping that keeps agents honest.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-14
---

# Architecture

*Start here after the [[README]] quickstart. The short version of the whole system: [[llm-wiki-pattern]].*

## Three layers

1. **Sources (`_inbox/`)** — immutable ground truth. PDFs, articles, exports dropped by the owner. Agents read, never modify (law 2). Re-compilation is always possible because originals never drift.
2. **Compiled pages (the seven category folders)** — small, linked, sourced markdown pages. Always rewritable; new sources make existing pages denser (law 6), never duplicated.
3. **Bookkeeping (root + `_meta/`)** — `index.md` (catalog), `log.md` (append-only op log), `hot.md` (recent-activity cache), `.manifest.json` (source hashes), [[taxonomy]] (controlled tags), [[manual]] (the owner's manual), and `_meta/templates/` (page scaffolds).

## The filing rule

Walk top-down, first match wins: dated? → `journal/` · one source's summary? → `references/` · proper noun? → `entities/` · followable steps? → `skills/` · combines multiple pages? → `synthesis/` · else → `concepts/`.

## Gotchas the design already absorbs

- `llm-wiki lint` does **not** skip `_inbox/` or `_meta/` — so `_meta/` files (including the page templates) carry full frontmatter, and `_inbox/` findings are exempted by law rather than "fixed".
- The seven page templates share a literal `{{title}}` placeholder, which lint reports as one warn-level `duplicate_titles` finding. Expected; documented in the README.
- Wikilinks are scanned in the full text of every file, code fences included — never write a double-bracket link unless that page exists.
- `_raw/` (the framework default) is intentionally absent: `_inbox/` is the single intake door.

*Next: [[configuration]]*
