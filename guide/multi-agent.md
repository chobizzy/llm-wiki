# Multi-Agent Operation

One vault can be co-managed by several agents (Claude Code, Hermes, Codex, …). Three mechanisms keep that safe:

## One constitution, many readers

`AGENTS.md` is the single rule file — laws, folders, and the CATEGORIES table that says where pages go. Agents that follow the AGENTS.md convention read it directly; Claude Code additionally imports it through `CLAUDE.md` (an `@AGENTS.md` include). Rules live in exactly one place, so agents can't diverge on law or on layout.

## Tagged, atomic operations

Every operation ends in one git commit (`wiki(<op>): <summary>`), and every `log.md` line carries `agent=<agent-name>`. When something looks wrong, `git log` plus the log answer *who did what, when* — no forensics required.

## Git as the lock

Law 9: an agent must never start a write operation while `git status` shows changes it didn't make — another agent may be mid-operation. It stops and reports to the owner instead. Combined with the atomic-commit rule, the working tree doubles as a cheap mutex.

## Backups

A vault created with `llm-wiki init --backup-hook` has a hook in `_meta/hooks/post-commit` that pushes every commit to `origin` (non-fatal when offline). Activate it once per clone with `git config core.hooksPath _meta/hooks`; the vault's `.gitattributes` pins the hook to LF endings so it survives Windows checkouts.

*Next: [maintenance loops](maintenance-loops.md)*
