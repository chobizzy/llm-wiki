---
title: Vault Manual
category: meta
tags: [meta, wiki-ops]
sources: [owner]
summary: Plain-English owner's manual — how to feed, ask, check, and fix this vault; what the agents do and what only you can do.
created: 2026-07-12
updated: 2026-07-14
---

# Vault Manual

*Read this when you forget how the vault works. Written in plain English on purpose.*

## What this is

One folder of markdown notes that your AI agents read and write for you. You drop raw material in; they distill it into short, linked, sourced notes. You browse the result in Obsidian. Nothing is ever silently deleted, and every change is a git commit, so everything can be undone.

## Your three doors

- **[[index]]** — the table of contents. Every page, one line each. Start here.
- **[[hot]]** — "what's new": recent activity, open threads, and contradictions waiting for you.
- **Obsidian's graph view** — see how notes connect. Isolated dots are usually new or neglected pages.

## How to feed it

| You want to… | Do / say this (to any agent) |
|---|---|
| Add a file, PDF, or article | Drop it in `_inbox/`, then say **"ingest my inbox"** |
| Save a web page | **"add this URL"** + the link |
| Save a thought or finding mid-conversation | **"save this to my wiki"** |
| Import agent history in bulk | **"process my Claude history"** (or the equivalent for your agent) |

## Page templates

In Obsidian: new note → command palette → **"Templates: Insert template"** → pick [[concept]], [[entity]], [[skill]], [[reference]], [[synthesis]], [[journal-entry]], or [[project]]. Each carries the frontmatter the constitution requires; the placeholder notes inside tell you what to replace.

## How to ask it

Just ask an agent: **"what do I know about X?"** — it answers from the vault and cites pages. Or browse in Obsidian and follow the links between pages.

## The weekly check (about 5 minutes)

Recommended: run these manually for the first couple of weeks before putting them on a schedule (graduated trust — skills log their gate outcomes to the [[trust-ledger]]).

1. Say **"run wiki-status"** — shows what's waiting to be ingested.
2. Say **"run wiki-lint"** — health report: broken links, orphan pages, missing sources. Findings inside `_inbox/` are normal and exempt — ignore them.
3. Open [[hot]] → **Flagged Contradictions**. Settling these is *your* job — the agents are forbidden from resolving disagreements silently.
4. Every few weeks: **"run wiki-lint --consolidate"** — the self-repair pass. It shows a preview and asks before writing anything.

## Reading a page's trust signals

Every page's frontmatter (the block at the top) tells you how much to trust it:

- **`lifecycle: draft`** — a machine wrote it and no human has checked it. When you've read a page and it's right, change the line to `reviewed` (or `verified`) yourself. Agents are not allowed to promote this — only you.
- **`^[inferred]`** at the end of a sentence — the AI's own conclusion, stated nowhere in the sources. **`^[ambiguous]`** — sources disagree.
- **`base_confidence`** (0–1) — how well sourced the page is. Below ~0.5 means one weak source; be skeptical.
- **`sources:`** — where it all came from. A claim with no source is a bug: tell an agent.

## Who does what

**You:** decide what goes in, promote `lifecycle`, settle contradictions, and read.
**The agents:** everything else — filing, linking, indexing, logging, committing.

## The seatbelt

Every operation ends in one git commit tagged `agent=<agent-name>`. To see history: `git log --oneline` in the vault folder, or read [[log]]. To undo something: tell an agent **"revert the last vault commit"**.

**Off-machine backup (optional):** point `origin` at a private GitHub repo, then run `git config core.hooksPath _meta/hooks` once inside the clone. From then on every commit is pushed automatically by the small hook in `_meta/hooks/`. If your PC dies, the vault is safe up to the last commit. Re-run the config command after every re-clone — hook activation does not travel with the repo.

## When something looks broken

| Symptom | What it means / what to do |
|---|---|
| Lint fails, but only on `_inbox/` files | Normal — exempt by the vault's own law. Ignore. |
| The wiki skills all stop working at once | The links to the `llm-wiki` repo broke (was the repo moved?). Say: **"re-run llm-wiki setup"** |
| The `llm-wiki` command itself disappears | A Python upgrade dropped the CLI — the skills are unaffected. Say: **"reinstall the llm-wiki CLI"** (`pip install -e` on the repo) |
| CLI crashes with strange box characters | Windows console quirk — set `PYTHONUTF8=1` |
| Two agents seem to conflict | Check [[log]] and `git log` — every change is tagged with who made it |
| A commit prints "[backup] push to GitHub failed" | You were offline — harmless. The next commit pushes everything. To force it now: `git push` in the vault folder |

## Deeper docs

- **AGENTS.md** (vault root) — the constitution every agent obeys.
- [[architecture]] — the three-layer design and why each piece exists.
- [[maintenance-loops]] — the full maintenance cadence design.
- [[trust-and-provenance]] — the lifecycle/confidence/provenance model in depth.
