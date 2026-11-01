---
title: Configuration
category: meta
tags: [meta, wiki-ops]
sources: [owner]
summary: How the llm-wiki config is resolved, the CLI commands that matter, and the setup facts that keep the skills working.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-21
---

# Configuration

## Config resolution

The wiki skills find your vault through the first match of:

1. An explicit `@name` vault override in your request (multi-vault setups; see the `wiki-switch` skill).
2. A local `.env` found by walking up from the working directory.
3. The global config at `~/.llm-wiki/config`.
4. If none exist, the agent runs the `wiki-setup` skill and interviews you.

`llm-wiki setup --vault /path/to/vault` writes the minimal global config (vault path, repo path, version) and links the skills into every detected agent. The config is flat `KEY="value"` lines — the optional keys (sources dir, categories, history paths, staged writes, token thresholds) are documented in the framework's `llm-wiki/SKILL.md`; copy what you need into the config.

## The CLI in one minute

| Command | What it does |
|---|---|
| `llm-wiki setup --vault <path>` | Link skills into your agents + write global config |
| `llm-wiki doctor [--vault <path>] [--strict]` | Health check: config, vault shape, skill installs |
| `llm-wiki lint <path> --json` | Frontmatter, broken links, duplicates, orphans |
| `llm-wiki info` / `list` | Install paths and bundled skills |
| `llm-wiki graph-query` / `graph-analyse` / `query` | Answer from the wikilink graph; find god nodes and communities |
| `llm-wiki batch-plan` / `cache-check` / `cache-update` | Split big ingests into batches; track source hashes in `.manifest.json` |
| `llm-wiki ast-extract <path>` | Code structure (classes/functions/imports) without an LLM |

## Warnings

- **Don't move or delete the `llm-wiki` repo checkout.** Agent skill directories hold links into it, not copies — relocating it silently breaks every skill. If you must move it, re-run `llm-wiki setup` afterwards. (On filesystems without symlink support, `setup --copy` installs copies instead.)
- **Windows:** set `PYTHONUTF8=1` before running the CLI — its box-drawing output crashes legacy console codepages.

*Next: [[multi-agent]]*
