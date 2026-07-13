---
title: LLM Wiki Vault Template
category: meta
tags: [meta]
sources: [owner]
summary: Quickstart and tour for this agent-maintained LLM wiki vault template.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-12
---

# LLM Wiki Vault Template

A ready-to-clone skeleton for a **Karpathy-style LLM wiki**: a knowledge base treated like a codebase, where raw sources are immutable input, AI agents are the compiler, and a wiki of small linked pages is the compiled artifact you browse in Obsidian (<https://obsidian.md>). It runs on the [obsidian-wiki](https://pypi.org/project/obsidian-wiki/) skill framework and is governed by a constitution (`AGENTS.md`) that any agent — Claude Code, Hermes, Codex, or others — obeys.

## Quickstart

1. **Use this template** (button above) to create your own repo, then clone it — e.g. to `~/Documents/my-wiki`.
2. **Install the framework:** `pip install obsidian-wiki`, then `obsidian-wiki setup --vault /path/to/your/clone`.
   ⚠️ Never run `obsidian-wiki setup --project` pointed at the vault — that mode overwrites `AGENTS.md`/`CLAUDE.md` with the framework's generic bootstrap.
3. **Open the folder as a vault in Obsidian.** The Templates core plugin is pre-wired to `_meta/templates/` — new note → command palette → *Templates: Insert template*.
4. **Windows only:** set `PYTHONUTF8=1` in the environment (the CLI's box-drawing output crashes legacy console codepages).
5. **Optional off-machine backup:** point `origin` at a private remote, then activate the auto-push hook once per clone:
   `git config core.hooksPath _meta/hooks`
6. **Verify:**

   ```
   obsidian-wiki doctor --vault .
   obsidian-wiki lint . --json
   ```

   Expected lint result: zero fail-level findings and exactly **one warning** — `duplicate_titles` for the seven files in `_meta/templates/`, which intentionally share the `{{title}}` placeholder.

Then drop a PDF or article into `_inbox/` and tell your agent: **"ingest my inbox."**

## What's inside

| Path | Purpose |
|---|---|
| `AGENTS.md` | The constitution — 10 laws, folder map, operations routing, DONE contract. Every agent reads it first. |
| `CLAUDE.md` | Claude Code entry point; imports `AGENTS.md`. |
| `index.md` / `log.md` / `hot.md` | Table of contents / append-only op log / "what's new" cache — agents keep these fresh. |
| `_inbox/` | The one intake door. Drop sources here; agents never modify them. |
| `concepts/ entities/ skills/ references/ synthesis/ journal/ projects/` | The seven page categories (see the filing rule in `AGENTS.md`). Seeded with one demo page each — replace with your own knowledge. |
| `_meta/` | System data: tag taxonomy, owner's manual, page templates, git hooks. |
| `docs/` | Human documentation: [architecture](docs/architecture.md), [configuration](docs/configuration.md), [multi-agent operation](docs/multi-agent.md), [maintenance loops](docs/maintenance-loops.md), [trust & provenance](docs/trust-and-provenance.md). |

## Credits

The LLM-maintained wiki pattern follows Andrej Karpathy's public writing on treating a personal knowledge base as LLM-compiled code. The skill framework is [ar9av/obsidian-wiki](https://pypi.org/project/obsidian-wiki/). MIT licensed.
