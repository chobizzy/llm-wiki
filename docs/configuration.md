---
title: Configuration
category: meta
tags: [meta, wiki-ops]
sources: [owner]
summary: How the obsidian-wiki config is resolved, the CLI commands that matter, and the one setup flag that can destroy your constitution.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-12
---

# Configuration

## Config resolution

The wiki skills find your vault through the first match of:

1. An explicit `@name` vault override in your request (multi-vault setups; see the `wiki-switch` skill).
2. A local `.env` found by walking up from the working directory.
3. The global config at `~/.obsidian-wiki/config`.
4. If none exist, the agent runs the `wiki-setup` skill and interviews you.

`obsidian-wiki setup --vault /path/to/vault` writes the minimal global config (vault path, framework path, version). The full set of optional keys — sources dir, categories, history paths, staged writes, token thresholds — is documented in the framework's `.env.example`; copy what you need into the config.

## The CLI in one minute

| Command | What it does |
|---|---|
| `obsidian-wiki setup --vault <path>` | Install skills into your agents + write global config |
| `obsidian-wiki doctor --vault <path>` | Health check: config, vault shape, skills, manifest |
| `obsidian-wiki lint <path> --json` | Frontmatter, broken links, duplicates, orphans |
| `obsidian-wiki info` / `list` | Install paths and bundled skills |
| `obsidian-wiki graph-query` / `graph-analyse` | Answer from the wikilink graph; find god nodes and communities |

## Warnings

- **Never run `obsidian-wiki setup --project` pointed at the vault.** The `--project` mode overwrites `AGENTS.md` and `CLAUDE.md` with the framework's generic bootstrap — your constitution would be replaced. Use `--vault` only.
- **Windows:** set `PYTHONUTF8=1` before running the CLI — its box-drawing output crashes legacy console codepages.

*Next: [[multi-agent]]*
