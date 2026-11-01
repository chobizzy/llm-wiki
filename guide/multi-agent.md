---
title: Multi-Agent Operation
category: meta
tags: [meta, agentic-systems]
sources: [owner]
summary: How multiple agents share one vault safely — a single constitution, tagged commits, and git as the coordination layer.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-12
---

# Multi-Agent Operation

One vault can be co-managed by several agents (Claude Code, Hermes, Codex, …). Three mechanisms keep that safe:

## One constitution, many readers

[[AGENTS]] is the single rule file. Agents that follow the AGENTS.md convention read it directly; Claude Code additionally imports it through [[CLAUDE]] (whose only content is an `@AGENTS.md` include). Rules live in exactly one place, so agents can't diverge on law.

## Tagged, atomic operations

Every operation ends in one git commit (`wiki(<op>): <summary>`), and every [[log]] line carries `agent=<agent-name>`. When something looks wrong, `git log` plus the log answer *who did what, when* — no forensics required.

## Git as the lock

Law 9: an agent must never start a write operation while `git status` shows changes it didn't make — another agent may be mid-operation. It stops and reports to the owner instead. Combined with the atomic-commit rule, the working tree doubles as a cheap mutex.

## Backups

The hook in `_meta/hooks/post-commit` pushes every commit to `origin` (non-fatal when offline). Activate it once per clone with `git config core.hooksPath _meta/hooks`; `.gitattributes` pins the hook to LF endings so it survives Windows checkouts.

*Next: [[maintenance-loops]]*
