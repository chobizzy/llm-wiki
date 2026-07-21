---
title: why agents need a constitution
category: synthesis
tags: [agentic-systems]
sources: ["[[llm-wiki-pattern]]", "[[karpathy-llm-wiki]]"]
summary: Combining the wiki pattern with multi-agent reality — durable laws in a versioned file beat prompt-time instructions once more than one agent writes.
lifecycle: draft
lifecycle_changed: "2026-07-12"
tier: core
base_confidence: 0.55
provenance: {extracted: 0.2, inferred: 0.7, ambiguous: 0.1}
relationships:
  - target: "[[llm-wiki-pattern]]"
    type: derived_from
  - target: "[[karpathy-llm-wiki]]"
    type: derived_from
created: 2026-07-12
updated: 2026-07-12
---

# why agents need a constitution

## The insight

The wiki pattern's rules (immutable sources, merge-don't-duplicate, index discipline) only hold if every writer obeys them — and prompt-time instructions don't survive across sessions, models, or agents. ^[inferred] A constitution file in the vault itself (AGENTS.md), read by every skill after config resolution, turns the rules into versioned, greppable law: numbered, each with a *never* or a *check*, enforced by a deterministic gate rather than the model's self-assessment.

## Pages combined

- [[llm-wiki-pattern]] contributes the rules worth enforcing (two layers, index front door, one-concept-one-page).
- [[karpathy-llm-wiki]] contributes the failure mode: unconstrained rewriting drifts the vault away from its sources.

## Conflicts surfaced

None yet between these two. The tension to watch is convenience vs. law: every law adds friction to writes, and a constitution nobody reads is worse than none. ^[inferred]
