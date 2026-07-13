---
title: ingest a source
category: skills
tags: [wiki-ops]
sources: ["agent:template session (2026-07-12)"]
summary: The compile loop — drop a source in _inbox, run wiki-ingest, pass the gates, commit.
lifecycle: draft
lifecycle_changed: "2026-07-12"
tier: core
base_confidence: 0.6
provenance: {extracted: 0.6, inferred: 0.4, ambiguous: 0.0}
relationships:
  - target: "[[llm-wiki-pattern]]"
    type: implements
created: 2026-07-12
updated: 2026-07-12
---

# ingest a source

## When to use

Any time `_inbox/` holds something not yet compiled into pages — a PDF, an article capture, an export.

## Steps

1. Drop the file into `_inbox/`. Never rename or edit it afterwards (law 2).
2. Tell your agent: **"ingest my inbox"** (the `wiki-ingest` skill of the [[obsidian-wiki-framework]]).
3. The agent distills into category pages per the filing rule, updating existing pages instead of duplicating (law 6).
4. Gates: `obsidian-wiki doctor` passes; `lint --json` shows zero fail-level findings outside `_inbox/`.
5. Bookkeeping plus one git commit (`wiki(ingest): …`) close the operation.

## Pitfalls

- A page without complete frontmatter is not done (law 4) — the gate catches it; don't hand-wave past it.
- Big drops: ingest in batches so each commit stays reviewable — see [[example-project]] for how a project page tracks multi-batch work.
