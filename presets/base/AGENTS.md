---
title: AGENTS
category: meta
tags: [meta]
sources: [owner]
summary: Constitution of this vault — laws, folder map, page categories, operations routing, and the DONE contract for all agents.
created: 2026-07-12
updated: 2026-11-02
---

# AGENTS.md — Constitution of This Vault

This vault is a Karpathy-style LLM wiki: a compiled knowledge base maintained by your AI agents (Claude Code, Hermes, or any agent that reads this file) and curated by its human owner. Every wiki skill MUST read this file after config resolution. These rules override framework defaults. Laws, not tips — each has a number, a never, or a check.

## NEVER (laws; exceptions require asking the owner first)

1. Never delete a wiki page. Supersede it: set `lifecycle: archived` and `superseded_by:` a wikilink to the successor page.
2. Never modify, move, or delete anything inside `_inbox/`. Layer-1 sources are immutable ground truth.
3. Never write wiki pages outside the folders in the CATEGORIES table below. System folders (`_*`) hold only their designated system data.
4. Never write a page without complete frontmatter: `title`, `category`, `tags`, `sources`, `summary`, `lifecycle`, `created`, `updated`. A page missing any of these is not done.
5. Never present a synthesized claim as extracted. Mark inferences `^[inferred]` and contested claims `^[ambiguous]`. Unmarked = paraphrase of a real source.
6. Never create a page for a concept that already has one. Grep `index.md` first; merge into the existing page. One concept = one page.
7. Never leave `index.md`, `log.md`, or `hot.md` stale after a write operation. Stale bookkeeping = the operation is not done.
8. Never commit secrets, API keys, tokens, or credentials into the vault.
9. Never start a write operation when `git status` shows uncommitted changes you did not make. Another agent may be mid-operation: stop and report to the owner.
10. Never set `lifecycle` above `draft` on pages you write. `reviewed`/`verified` are human-only transitions.
11. Never stamp a timestamp with a `Z` suffix unless it is true UTC. `log.md` entries and ISO frontmatter timestamps come from a UTC clock (`date -u` or equivalent) — never local time relabeled as Z. Check: a new timestamp must not be in the future relative to `date -u`.

## FOLDERS

System folders hold system data, never wiki pages.

| Folder | Contents | Agent access |
|---|---|---|
| `_inbox/` | Owner-dropped source documents (PDFs, articles, exports). THE one intake door. | Read-only. Ingest reads; never moves or edits. |
| `_meta/` | `taxonomy.md` tag vocabulary; Bases dashboards; `templates/` page templates (Obsidian core Templates); `hooks/` git hooks, when backup is on; `trust-ledger.md` per-skill gate outcomes, started by the first skill that logs one | Via `tag-taxonomy` / `wiki-dashboard`; templates read-only at write time; trust ledger append-only after a skill's gate |
| `_staging/` | Review queue when `WIKI_STAGED_WRITES=true`; created on first use | Ingest writes; `wiki-stage-commit` promotes |
| `_archives/` | Vault snapshots from `wiki-rebuild`; created on first use | Write-once during rebuild |

`_raw/` is intentionally absent. If a drop-to-raw flow requires it, create it on demand — do not route normal captures through it; distill directly to category pages.

## CATEGORIES

Wiki pages live only in these folders (law 3). To file a page, walk the rows top-down: the first row whose *Holds* fits the page wins, and the last row takes everything else. Set the page's `category:` to its folder name unless its row says otherwise. *Role* is the built-in part a folder plays for the skills (see `llm-wiki/SKILL.md`); a role no row claims falls to the last row.

To change the folders, edit this table, then create or rename the folder to match — or ask an agent to ("add a recipes folder to my wiki"). `llm-wiki lint` and `llm-wiki doctor` read this table: keep one row per folder, lowercase folder names, and no `|` inside a cell.

<!-- llm-wiki init writes the CATEGORIES table here -->

## OPERATIONS

| Intent | Skill |
|---|---|
| Save a finding from this session | `wiki-capture` |
| Distill documents from `_inbox/` | `wiki-ingest` |
| Answer a question from the vault | `wiki-query` |
| Freshness check, index, hot.md refresh | `daily-update` |
| Health audit / dream cycle | `wiki-lint` (`--consolidate`) |
| Weave links between pages | `cross-linker` |
| Mine agent histories | the framework's `*-history-ingest` family (`claude-history-ingest`, `hermes-history-ingest`) |
| Cross-source insight pages | `wiki-synthesize` |
| Add or change the vault's folders | `wiki-setup` |

Config: `~/.llm-wiki/config` (see Config Resolution Protocol in `llm-wiki/SKILL.md`). Deterministic gate after write operations: `llm-wiki doctor` passes, and `llm-wiki lint --json` shows zero fail-level findings (`broken_links`, `missing_frontmatter`, `invalid_lifecycle`, `invalid_layout`) outside `_inbox/`. Findings inside `_inbox/` are exempt: sources are immutable (law 2) and the CLI does not skip that folder.

## DONE (an operation is complete ONLY when all six hold)

1. Pages written with full frontmatter (law 4) and double-bracket wikilinks to related pages.
2. `.manifest.json` updated for every source touched (absolute expanded paths as keys; `pages_created`/`pages_updated` populated).
3. `log.md` appended: `- [ISO-8601Z] OPERATION agent=<agent-name> key=value …`
4. `hot.md` refreshed with a one-line summary of what changed.
5. `index.md` reconciled (every page listed exactly once: list item with a wikilink, an em-dash one-line summary, then tags).
6. `git commit` created with message `wiki(<op>): <summary>`. Uncommitted work = not done.

Anything less than all six is a partial operation: finish it or report it as incomplete. Never report done from your own assessment — done = the checks above pass.
