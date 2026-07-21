---
title: AGENTS
category: meta
tags: [meta]
sources: [owner]
summary: Constitution of this vault — laws, folder map, operations routing, and the DONE contract for all agents.
created: 2026-07-12
updated: 2026-07-14
---

# AGENTS.md — Constitution of This Vault

This vault is a Karpathy-style LLM wiki: a compiled knowledge base maintained by your AI agents (Claude Code, Hermes, or any agent that reads this file) and curated by its human owner. Every wiki skill MUST read this file after config resolution. These rules override framework defaults. Laws, not tips — each has a number, a never, or a check.

## NEVER (laws; exceptions require asking the owner first)

1. Never delete a wiki page. Supersede it: set `lifecycle: archived` and `superseded_by:` a wikilink to the successor page.
2. Never modify, move, or delete anything inside `_inbox/`. Layer-1 sources are immutable ground truth.
3. Never write wiki pages outside `concepts/`, `entities/`, `skills/`, `references/`, `synthesis/`, `journal/`, `projects/`. System folders (`_*`) hold only their designated system data.
4. Never write a page without complete frontmatter: `title`, `category`, `tags`, `sources`, `summary`, `lifecycle`, `created`, `updated`. A page missing any of these is not done.
5. Never present a synthesized claim as extracted. Mark inferences `^[inferred]` and contested claims `^[ambiguous]`. Unmarked = paraphrase of a real source.
6. Never create a page for a concept that already has one. Grep `index.md` first; merge into the existing page. One concept = one page.
7. Never leave `index.md`, `log.md`, or `hot.md` stale after a write operation. Stale bookkeeping = the operation is not done.
8. Never commit secrets, API keys, tokens, or credentials into the vault.
9. Never start a write operation when `git status` shows uncommitted changes you did not make. Another agent may be mid-operation: stop and report to the owner.
10. Never set `lifecycle` above `draft` on pages you write. `reviewed`/`verified` are human-only transitions.

## FOLDERS

| Folder | Contents | Agent access |
|---|---|---|
| `_inbox/` | Owner-dropped source documents (PDFs, articles, exports). THE one intake door. | Read-only. Ingest reads; never moves or edits. |
| `_staging/` | Review queue (unused unless `WIKI_STAGED_WRITES=true`) | Unused |
| `_archives/` | Vault snapshots from `wiki-rebuild` | Write-once during rebuild |
| `_meta/` | `taxonomy.md` tag vocabulary; Bases dashboards; `templates/` page templates (Obsidian core Templates); `hooks/` git hooks | Via `tag-taxonomy` / `wiki-dashboard`; templates read-only at write time |
| `docs/` | Repo documentation for humans — not wiki pages | Read-only |
| `concepts/` | One page per standalone idea, pattern, mental model | Read/write |
| `entities/` | One page per proper noun: tool, person, org, product | Read/write |
| `skills/` | One page per reusable procedure/how-to (knowledge, NOT agent skills) | Read/write |
| `references/` | One page per ingested source; single-source view, cites `_inbox/` original | Read/write |
| `synthesis/` | Insights that only exist by combining multiple pages | Read/write |
| `journal/` | Dated session logs and observations (`YYYY-MM-DD.md`) | Read/write |
| `projects/` | One page per project: `projects/<name>.md`. Nest to `projects/<name>/<name>.md` + scoped subdirs only when a project exceeds ~5 related pages. Never `_project.md`. | Read/write |

`_raw/` is intentionally absent. If a drop-to-raw flow requires it, create it on demand — do not route normal captures through it; distill directly to category pages.

Filing rule (walk top-down, first match wins): dated? → `journal/` · one source's summary? → `references/` · proper noun? → `entities/` · followable steps? → `skills/` · combines multiple pages? → `synthesis/` · else → `concepts/`.

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

Config: `~/.llm-wiki/config` (see Config Resolution Protocol in `llm-wiki/SKILL.md`). Deterministic gate after write operations: `llm-wiki doctor` passes, and `llm-wiki lint --json` shows zero fail-level findings (`broken_links`, `missing_frontmatter`) outside `_inbox/`. Findings inside `_inbox/` are exempt: sources are immutable (law 2) and the CLI does not skip that folder.

## DONE (an operation is complete ONLY when all six hold)

1. Pages written with full frontmatter (law 4) and double-bracket wikilinks to related pages.
2. `.manifest.json` updated for every source touched (absolute expanded paths as keys; `pages_created`/`pages_updated` populated).
3. `log.md` appended: `- [ISO-8601Z] OPERATION agent=<agent-name> key=value …`
4. `hot.md` refreshed with a one-line summary of what changed.
5. `index.md` reconciled (every page listed exactly once: list item with a wikilink, an em-dash one-line summary, then tags).
6. `git commit` created with message `wiki(<op>): <summary>`. Uncommitted work = not done.

Anything less than all six is a partial operation: finish it or report it as incomplete. Never report done from your own assessment — done = the checks above pass.
