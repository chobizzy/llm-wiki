---
title: obsidian-wiki framework
category: entities
tags: [tools]
sources: ["https://pypi.org/project/obsidian-wiki/"]
summary: The pip-installable skill framework this vault runs on — 36 agent skills, a deterministic CLI (doctor/lint), and a shared config.
lifecycle: draft
lifecycle_changed: "2026-07-12"
tier: supporting
base_confidence: 0.7
provenance: {extracted: 0.8, inferred: 0.2, ambiguous: 0.0}
relationships:
  - target: "[[llm-wiki-pattern]]"
    type: implements
created: 2026-07-12
updated: 2026-07-12
---

# obsidian-wiki framework

The engine under this vault: `pip install obsidian-wiki` ships ~36 agent skills (ingest, query, lint, synthesize, history mining) plus a deterministic CLI whose `doctor` and `lint` commands are this vault's DONE gates.

## What it is

- Skills are markdown playbooks (`SKILL.md`) installed by symlink into each agent's skill directory — one canonical copy, many readers.
- The CLI is the non-LLM half: config writing, health checks, link/frontmatter linting, graph queries, source hashing.
- Config lives at `~/.obsidian-wiki/config`; this vault's own `AGENTS.md` overrides framework defaults.

## Why it's in this vault

It implements the [[llm-wiki-pattern]] without hand-rolling the machinery; the compile loop it enables is documented in [[ingest-a-source]].

## Operational notes

Upgrades (`pip install --upgrade`) replace the skill files — never edit them in place. On Windows, run the CLI with `PYTHONUTF8=1`.
