# Maintenance Loops

A wiki that isn't maintained on a loop decays into a notes folder. The loops, smallest to largest:

| Loop | Cadence | Skill | What it does |
|---|---|---|---|
| Capture | per session | `wiki-capture` | Save findings from the current conversation |
| Ingest | when `_inbox/` has items | `wiki-ingest` | Compile sources into category pages |
| Daily update | daily | `daily-update` | Freshness check, index reconcile, hot-cache refresh |
| Lint | weekly | `wiki-lint` | Report-only health audit: broken links, orphans, schema drift |
| Consolidate | every few weeks | `wiki-lint --consolidate` | The "dream cycle": self-repair with preview + confirmation |
| Synthesize | when clusters form | `wiki-synthesize` | Cross-source insight pages |

## Graduated trust

Don't automate on day one. Run every loop manually until it has succeeded a few times under your eyes, then move it to a schedule (cron, scheduled agents, or your agent's native scheduler). Autonomy is earned per loop, not granted globally — if a scheduled loop misbehaves, demote it back to manual. Skills record their gate outcomes in `_meta/trust-ledger.md`, so the pass rate is there to check.

## The owner's five minutes

The one loop agents can't do: reading the Flagged Contradictions in `hot.md` and settling them, and promoting `lifecycle` on pages you've verified — see [trust and provenance](trust-and-provenance.md).

*Next: [trust and provenance](trust-and-provenance.md)*
