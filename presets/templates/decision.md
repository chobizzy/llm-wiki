---
title: "{{title}}"
category: __CATEGORY__
tags: []
sources: []
summary: One sentence — what was decided and the main reason.
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

One page per decision. Write it when the choice is made — the reasons are the part everyone forgets.

## Context

What forced a choice.

## Options considered

Each option and what it would have cost.

## Decision

What was chosen, by whom, and when.

## Why

The reasons. Mark reasoning nobody stated outright `^[inferred]`.

## Placeholder notes (delete on use)

The example relationship above points at [[index]] so lint resolves — replace it with links to real pages. If a later decision replaces this one, set `lifecycle: archived` and `superseded_by:` instead of deleting it.
