# Architecture

*The design of an llm-wiki vault: three layers, one table that says where pages go, and the bookkeeping that keeps agents honest. Start from the [project README](../README.md).*

## Three layers

1. **Sources (`_inbox/`)** — immutable ground truth. PDFs, articles, exports dropped by the owner. Agents read, never modify (law 2). Re-compilation is always possible because originals never drift.
2. **Compiled pages (the category folders)** — small, linked, sourced markdown pages, filed into the folders the vault's CATEGORIES table lists. Always rewritable; new sources make existing pages denser (law 6), never duplicated.
3. **Bookkeeping (root + `_meta/`)** — `AGENTS.md` (the constitution, CATEGORIES table included), `index.md` (catalog), `log.md` (append-only op log), `hot.md` (recent-activity cache), `.manifest.json` (source hashes), `README.md` (the owner's manual), `_meta/taxonomy.md` (controlled tags), and `_meta/templates/` (page scaffolds).

## Where pages go

Every vault declares its page folders in the CATEGORIES table of its `AGENTS.md` — `Folder | Holds | Role`, one row per folder. An agent files a page by walking the rows top-down: the first row whose *Holds* fits wins, and the last row takes everything else. Law 3 forbids pages anywhere else. [Layouts](layouts.md) covers the packs, the roles, and changing the table.

`llm-wiki lint`, `doctor` and `layout` read the same table, so the gate always checks the layout the vault actually has.

## Gotchas the design already absorbs

- `llm-wiki lint` does **not** skip `_inbox/` or `_meta/` — so `_meta/` files (including the page templates) carry full frontmatter, and `_inbox/` findings are exempted by law rather than "fixed".
- Page templates share a literal `{{title}}` placeholder, which lint reports as one warn-level `duplicate_titles` finding whenever a vault has more than one template. Expected.
- Wikilinks are scanned in the full text of every file, code fences included — never write a double-bracket link unless that page exists. A markdown link whose target ends in `.md` counts as a page link too, even when it points at a website.
- Templates link to `[[index]]` instead of to each other, so any template can be added or removed without breaking a link.
- `_raw/` (the framework default) is intentionally absent: `_inbox/` is the single intake door. `_staging/`, `_archives/` and `_meta/trust-ledger.md` appear when first used.

*Next: [layouts](layouts.md)*
