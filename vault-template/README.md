---
title: LLM Wiki Vault Template
category: meta
tags: [meta]
sources: [owner]
summary: Quickstart and tour for this agent-maintained LLM wiki vault template.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-21
---

# LLM Wiki Vault Template

A ready-to-clone skeleton for a **Karpathy-style LLM wiki**: a knowledge base treated like a codebase, where raw sources are immutable input, AI agents are the compiler, and a wiki of small linked pages is the compiled artifact you browse in Obsidian (<https://obsidian.md>). It runs on the self-owned **llm-wiki** skill framework — a git repo of 32 agent skills plus a stdlib-only CLI — and is governed by a constitution (`AGENTS.md`) that any agent — Claude Code, Hermes, or others — obeys.

## Quickstart

1. **Copy this folder** to where you want your vault — e.g. `cp -r vault-template ~/Documents/my-wiki` — then `git init` it and make the first commit.
2. **Install the framework:** this folder ships inside the [llm-wiki](https://github.com/chobizzy/llm-wiki) repo. `pip install -e /path/to/llm-wiki`, then `llm-wiki setup --vault /path/to/your/vault`.
   Skills are linked from the repo checkout into your agents' skill directories — keep that checkout in place, and re-run `setup` if you move it.
3. **Open the folder as a vault in Obsidian.** The Templates core plugin is pre-wired to `_meta/templates/` — new note → command palette → *Templates: Insert template*.
4. **Windows only:** set `PYTHONUTF8=1` in the environment (the CLI's box-drawing output crashes legacy console codepages).
5. **Optional off-machine backup:** point `origin` at a private remote, then activate the auto-push hook once per clone:
   `git config core.hooksPath _meta/hooks`
6. **Verify:**

   ```
   llm-wiki doctor --vault .
   llm-wiki lint . --json
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

The LLM-maintained wiki pattern follows Andrej Karpathy's public writing on treating a personal knowledge base as LLM-compiled code. The skill framework is [llm-wiki](https://github.com/chobizzy/llm-wiki) — this template ships inside it (MIT licensed, see the repo root `LICENSE`).
