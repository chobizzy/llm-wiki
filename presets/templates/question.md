---
title: "{{title}}"
category: __CATEGORY__
tags: []
sources: []
summary: One sentence — the question and the current best answer.
lifecycle: draft
lifecycle_changed: "{{date}}"
tier: core
base_confidence: 0.5
provenance: {extracted: 0.0, inferred: 0.0, ambiguous: 0.0}
relationships:
  - target: "[[index]]"
    type: related_to
created: "{{date}}"
updated: "{{date}}"
---

# {{title}}

One page per open question you are researching. Phrase the title as the question; the page holds your current best answer and changes as evidence arrives.

## Current answer

The best answer so far and how sure you are. Mark it `^[inferred]` where no source says it directly.

## Evidence

Wikilinks to the pages that support or undercut the answer, and what each one adds.

## What would change the answer

The source, experiment, or number you are still missing.

## Placeholder notes (delete on use)

The example relationship above points at [[index]] so lint resolves — replace it with links to real pages. Keep `lifecycle: draft`.
