---
title: "{{title}}"
category: __CATEGORY__
tags: []
sources: []
summary: One sentence — what this meeting decided.
lifecycle: draft
lifecycle_changed: "{{date}}"
tier: supporting
base_confidence: 0.5
provenance: {extracted: 0.0, inferred: 0.0, ambiguous: 0.0}
relationships:
  - target: "[[index]]"
    type: related_to
created: "{{date}}"
updated: "{{date}}"
---

# {{title}}

One page per meeting, named `YYYY-MM-DD-topic`. Cite the transcript or notes from `_inbox/` in `sources`.

## Who was there

Names, linked to their pages when they have one.

## What was decided

One line per decision. A decision that needs its options and reasons spelled out gets its own page, linked from here.

## Follow-ups

Who does what, by when.

## Placeholder notes (delete on use)

The example relationship above points at [[index]] so lint resolves — replace it with links to real pages. Keep `lifecycle: draft`.
