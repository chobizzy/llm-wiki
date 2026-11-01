# Trust and Provenance

Machine-written knowledge needs machine-readable honesty. Four signals, all visible in a page's frontmatter or body:

## Lifecycle (who has vouched for this?)

`draft` → `reviewed` → `verified`, plus `archived` (with `superseded_by:`) instead of deletion. Agents may only ever write `draft` (law 10) and may never delete (law 1). Promotion is a human act: you read the page, you edit the line. This single rule makes "has a human checked this?" a grep-able fact.

## base_confidence (how well is it sourced?)

0–1 in frontmatter. Rough guide: a single weak source lands around 0.4; multiple agreeing primary sources push toward 0.8+. Below ~0.5, be skeptical and check `sources:` yourself.

## provenance (what kind of claims are these?)

`provenance: {extracted, inferred, ambiguous}` — the fractions of the page paraphrased from sources, concluded by the model, or contested between sources. A synthesis page being mostly `inferred` is honest; a reference page being mostly `inferred` is a bug.

## Inline markers (which sentence, exactly?)

`^[inferred]` ends a sentence the model concluded on its own; `^[ambiguous]` ends a claim the sources disagree on. Unmarked sentences must paraphrase a real source (law 5). Contradictions are surfaced in `hot.md`, never silently resolved: once more than one agent writes, the only defence against a vault that quietly repeats its own guesses is laws in a file plus a gate that checks them.

*Back to: [architecture](architecture.md)*
