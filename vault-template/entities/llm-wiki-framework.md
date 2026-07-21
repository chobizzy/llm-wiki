---
title: llm-wiki framework
category: entities
tags: [tools]
sources: ["https://github.com/chobizzy/llm-wiki"]
summary: The self-owned skill framework this vault runs on — 32 agent skills as git-tracked files, a deterministic stdlib-only CLI (doctor/lint), and a shared config.
lifecycle: draft
lifecycle_changed: "2026-07-12"
tier: supporting
base_confidence: 0.7
provenance: {extracted: 0.8, inferred: 0.2, ambiguous: 0.0}
relationships:
  - target: "[[llm-wiki-pattern]]"
    type: implements
created: 2026-07-12
updated: 2026-07-14
---

# llm-wiki framework

The engine under this vault: the self-owned `llm-wiki` git repo ships 32 agent skills (ingest, query, lint, synthesize, history mining) plus a deterministic, stdlib-only CLI whose `doctor` and `lint` commands are this vault's DONE gates. It replaced the third-party `obsidian-wiki` pip package (2026-07-13) so the skills are owned files under version control, not artifacts inside site-packages.

## What it is

- Skills are markdown playbooks (`SKILL.md`) living as real files in the repo's `skills/`; `llm-wiki setup` links them into each agent's skill directory — one canonical git-tracked copy, many readers, never a copy in site-packages.
- The CLI is the non-LLM half: config writing, health checks, link/frontmatter linting, graph queries, ingest batching, source hashing.
- Config lives at `~/.llm-wiki/config` (flat `KEY="value"` lines); this vault's own `AGENTS.md` overrides framework defaults.

## Why it's in this vault

It implements the [[llm-wiki-pattern]] without hand-rolling the machinery; the compile loop it enables is documented in [[ingest-a-source]].

## Operational notes

Edit skills in the repo and commit — agent directories only hold links to the checkout, so keep the repo in place (re-run `llm-wiki setup` if it moves). A `pip uninstall` or Python upgrade can break the CLI executable (fix: `pip install -e` on the repo again) but never the installed skills. On Windows, run the CLI with `PYTHONUTF8=1`.
