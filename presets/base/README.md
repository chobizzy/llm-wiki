---
title: Vault Manual
category: meta
tags: [meta, wiki-ops]
sources: [owner]
summary: How this vault works — feeding it, asking it, checking it, and changing its folders; what the agents do and what only you can do.
created: 2026-07-12
updated: 2026-11-02
---

# Vault Manual

*Read this when you forget how the vault works. Written in plain English on purpose.*

## What this is

One folder of markdown notes that your AI agents read and write for you. You drop raw material in; they distill it into short, linked, sourced notes. You browse the result in Obsidian. Nothing is ever silently deleted, and every change is a git commit, so everything can be undone.

It runs on the [llm-wiki](https://github.com/chobizzy/llm-wiki) framework: agent skills plus a small `llm-wiki` command-line tool. [[AGENTS]] is the constitution every agent obeys.

## What's inside

| Path | What it is |
|---|---|
| [[AGENTS]] | The laws, the system folders, and the CATEGORIES table that says which folders hold pages |
| [[index]] | The table of contents: every page, one line each |
| [[hot]] | "What's new": recent activity, open threads, and contradictions waiting for you |
| [[log]] | Append-only record of every operation |
| `_inbox/` | Drop sources here. Agents read them and never change them |
| `_meta/` | [[taxonomy]] (the tag vocabulary) and `templates/` (page templates) |
| `.manifest.json` | A fingerprint of every ingested source, so re-ingesting an unchanged file does nothing |
| Category folders | Your pages, filed by the CATEGORIES table in [[AGENTS]] |

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

## How to ask it

Just ask an agent: **"what do I know about X?"** — it answers from the vault and cites pages. Or browse in Obsidian and follow the links between pages.

## Page templates

In Obsidian: new note → command palette → **"Templates: Insert template"** → pick the template named after the kind of page you're writing. Each carries the frontmatter the constitution requires; the placeholder notes inside tell you what to replace.

## Changing the folders

The folders that hold pages are the CATEGORIES table in [[AGENTS]]. To add one, add a row (the folder, what it holds, and usually no role), create the folder, and optionally put a page template in `_meta/templates/`. Or just ask an agent: **"add a recipes folder to my wiki"**.

Rows are checked top-down, so keep specific folders above general ones; the last row catches everything else. Rename or remove a folder only while it is empty — pages already filed there would need moving too.

## The weekly check (about 5 minutes)

Recommended: run these manually for the first couple of weeks before putting them on a schedule (graduated trust — skills record their gate outcomes in `_meta/trust-ledger.md` once they start running).

1. Say **"run wiki-status"** — shows what's waiting to be ingested.
2. Say **"run wiki-lint"** — health report: broken links, orphan pages, missing sources. Findings inside `_inbox/` are normal and exempt — ignore them.
3. Open [[hot]] → **Flagged Contradictions**. Settling these is *your* job — the agents are forbidden from resolving disagreements silently.
4. Every few weeks: **"run wiki-lint --consolidate"** — the self-repair pass. It shows a preview and asks before writing anything.

You can run the deterministic checks yourself, too: `llm-wiki doctor --vault .` and `llm-wiki lint .` in the vault folder. A healthy vault has no fail-level findings.

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

**Off-machine backup (optional):** if this vault was created with the backup hook (`_meta/hooks/post-commit`), point `origin` at a private GitHub repo and run `git config core.hooksPath _meta/hooks` once inside the clone. From then on every commit is pushed automatically. Re-run the config command after every re-clone — hook activation does not travel with the repo.

## When something looks broken

| Symptom | What it means / what to do |
|---|---|
| Lint fails, but only on `_inbox/` files | Normal — exempt by the vault's own law. Ignore. |
| Lint reports `invalid_layout` | The CATEGORIES table in [[AGENTS]] has a typo. The finding names the problem; fix that row. |
| The wiki skills all stop working at once | The links to the `llm-wiki` repo broke (was the repo moved?). Say: **"re-run llm-wiki setup"** |
| The `llm-wiki` command itself disappears | A Python upgrade dropped the CLI — the skills are unaffected. Say: **"reinstall the llm-wiki CLI"** (`pip install -e` on the repo) |
| CLI crashes with strange box characters | Windows console quirk — set `PYTHONUTF8=1` |
| Two agents seem to conflict | Check [[log]] and `git log` — every change is tagged with who made it |
| A commit prints "[backup] push to GitHub failed" | You were offline — harmless. The next commit pushes everything. To force it now: `git push` in the vault folder |

## Deeper docs

The framework's [guide](https://github.com/chobizzy/llm-wiki/tree/main/guide) covers the design in depth: the three-layer architecture, configuration, running several agents on one vault, the maintenance loops, and the trust and provenance model.
