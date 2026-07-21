---
title: Maintenance Loops
category: meta
tags: [meta, wiki-ops]
sources: [owner]
summary: The recurring loops that keep the vault healthy — capture, ingest, daily update, lint, consolidate, synthesize — and the graduated-trust rollout.
lifecycle: draft
created: 2026-07-12
updated: 2026-07-12
---

# Maintenance Loops

A wiki that isn't maintained on a loop decays into a notes folder. The loops, smallest to largest:

| Loop | Cadence | Skill | What it does |
|---|---|---|---|
| Capture | per session | `wiki-capture` | Save findings from the current conversation |
| Ingest | when `_inbox/` has items | `wiki-ingest` | Compile sources into category pages (see [[ingest-a-source]]) |
| Daily update | daily | `daily-update` | Freshness check, index reconcile, hot-cache refresh |
| Lint | weekly | `wiki-lint` | Report-only health audit: broken links, orphans, schema drift |
| Consolidate | every few weeks | `wiki-lint --consolidate` | The "dream cycle": self-repair with preview + confirmation |
| Synthesize | when clusters form | `wiki-synthesize` | Cross-source insight pages |

## Graduated trust

Don't automate on day one. Run every loop manually until it has succeeded a few times under your eyes, then move it to a schedule (cron, scheduled agents, or your agent's native scheduler). Autonomy is earned per loop, not granted globally — if a scheduled loop misbehaves, demote it back to manual.

## The owner's five minutes

The one loop agents can't do: reading [[hot]]'s Flagged Contradictions and settling them, and promoting `lifecycle` on pages you've verified — see [[trust-and-provenance]].

*Next: [[trust-and-provenance]]*
