---
title: LLM Wiki Pattern
category: concepts
tags: [knowledge-management]
sources: ["[[karpathy-llm-wiki]]"]
summary: Treat a knowledge base like a codebase — immutable raw sources compiled by an LLM into a linked wiki of small pages behind an index front door.
lifecycle: draft
lifecycle_changed: "2026-07-12"
tier: core
base_confidence: 0.7
provenance: {extracted: 0.6, inferred: 0.4, ambiguous: 0.0}
relationships:
  - target: "[[obsidian-wiki-framework]]"
    type: related_to
  - target: "[[why-agents-need-a-constitution]]"
    type: related_to
created: 2026-07-12
updated: 2026-07-12
---

# LLM Wiki Pattern

Treat knowledge like code: Obsidian as the editor, the model as the programmer, the wiki as the compiled artifact. Three load-bearing rules keep the compilation honest:

1. **Two layers, strictly separated.** Raw sources in `_inbox/` are immutable ground truth; compiled pages are always rewritable. Recompiling from originals prevents meaning drift — without it, repeated rewrites compound small errors until the vault confidently repeats its own inventions. ^[inferred]
2. **An index front door.** Every page gets one line in the index, so agents know what exists without opening everything.
3. **Small linked pages, merged not duplicated.** One idea per file; new sources make existing pages denser, not folders longer. Links are half the value: a linked wiki gets stronger as it grows where a search dump gets noisier.

See [[karpathy-llm-wiki]] for the originating source, [[ingest-a-source]] for the compile loop this vault uses, and [[why-agents-need-a-constitution]] for how the rules are enforced.
