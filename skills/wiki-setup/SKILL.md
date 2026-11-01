---
name: wiki-setup
description: >
  Create a new llm-wiki vault by interviewing the user — which pack (standard or minimal), what they'll use it
  for (learner, researcher, indie hacker, content creator, team, personal), and any folders of their own — or
  change the folders of an existing vault. Use when the user says "set up my wiki", "create a new vault",
  "initialize obsidian", "get started with the wiki", "which folders should my wiki have", "add a recipes
  folder to my wiki", "change my vault's folders", or needs to reconfigure or repair a broken setup.
---

# Wiki Setup — Create a Vault, or Change Its Folders

Two modes:

- **Create** — there is no vault yet: interview the user, then build it with `llm-wiki init`.
- **Change folders** — the vault exists: add, rename, or remove a folder in its CATEGORIES table.

Never hand-build a vault with `mkdir`. `llm-wiki init` writes the constitution, the CATEGORIES table, the page templates, and the bookkeeping files, and every combination it can produce passes the gate. Folder names come only from the user's answers — never invent a layout.

## Mode A: Create a vault

### Step 1: Where

Ask where the vault should live: a new or empty folder (default `~/Documents/llm-wiki`). Expand it to an absolute path. If the folder exists and is not empty, stop — init never overwrites. If it already holds a vault (it has an `AGENTS.md`), switch to Mode B.

### Step 2: Interview

Get the current options with `llm-wiki presets --json` (packs, roles, add-on folders). Then ask these, in order, one at a time. Use your multiple-choice question tool if you have one; in Claude Code, show each pack's folder tree as the option preview.

1. **Which pack?**
   - **standard** (default) — `references/ entities/ synthesis/ concepts/`: one folder per page type in Karpathy's LLM-wiki gist.
   - **minimal** — a single `wiki/` folder, as in the gist. Pages keep their kind in `category:`.
2. **What will you use it for?** Standard only. Pick any, or none — each role adds a folder or two:

   | Role | Adds |
   |---|---|
   | Learner — courses, books, self-study | `courses/` |
   | Researcher — papers and reports, building a thesis | `questions/` |
   | Indie hacker — building products on your own | `projects/` |
   | Content creator — research for posts, videos, newsletters | `ideas/`, `outputs/` |
   | Team — a shared wiki fed by meetings, chats and docs | `meetings/`, `decisions/` |
   | Personal — goals, health, reflections | `journal/` |

   If the user answers in their own words ("I build SaaS and post on YouTube"), map it to roles yourself and confirm: *"That's indie hacker + content creator: adds projects/, ideas/ and outputs/. OK?"*
3. **Any folder of your own?** Standard only, optional. A name and one line of what it holds, e.g. `recipes — cooking recipes: ingredients and steps`. Names use lowercase letters, digits and hyphens.
4. **Extras:**
   - Demo pages that show the conventions — default yes for a first vault.
   - A git hook that pushes every commit to a GitHub remote — default no.
   - Staged writes (agent edits wait in `_staging/` until the owner approves them) — default yes for the team role, otherwise no.

Keep the interview short. Structure is earned, not designed upfront, and the table is easy to change later. Don't offer renames unless the user asks for one.

### Step 3: Preview, then confirm

Run `llm-wiki init <path> <flags> --dry-run` and show the user the folder tree and CATEGORIES table it prints. The flags:

| Answer | Flag |
|---|---|
| pack | `--pack standard` or `--pack minimal` |
| each role | `--role learner` (repeat per role: `researcher`, `indie-hacker`, `creator`, `team`, `personal`) |
| each folder of their own | `--folder recipes="Cooking recipes: ingredients and steps"` |
| a rename the user asked for | `--rename concepts=notes` |
| no demo pages | `--no-demo` |
| backup hook | `--backup-hook` |

Create the vault only after the user says yes.

### Step 4: Create and connect

1. `llm-wiki init <path> <same flags>`.
2. `llm-wiki setup --vault <path>` — links the skills into the user's agents and writes `~/.llm-wiki/config`.
3. If the user chose staged writes, set `WIKI_STAGED_WRITES="true"` in `~/.llm-wiki/config` (flat `KEY="value"` lines; keep every other key).
4. Offer to make the first commit inside the vault: `git init && git add -A && git commit -m "init: vault from the llm-wiki <pack> pack"`. Git is what makes every later operation undoable (law 9, DONE item 6), but ask first — it's the user's folder.
5. If they chose the backup hook: tell them to add a private remote, then run `git config core.hooksPath _meta/hooks` in the vault.
6. Verify: `llm-wiki doctor --vault <path>` passes, including `vault-layout`, and `llm-wiki lint <path> --json` has no fail-level findings. A fresh standard vault shows exactly one warning (`duplicate_titles` for the page templates, which share the `{{title}}` placeholder); a fresh minimal vault shows none.

Then tell the user what to do next: open the folder as a vault in Obsidian, drop a source in `_inbox/`, and say "ingest my inbox". If they picked the indie hacker role, suggest "process my Claude history" to mine their past sessions.

Recommended Obsidian community plugins (the user installs them): **Dataview** (query page metadata), **Templater** (if they write pages by hand), **Obsidian Git** (backups from inside Obsidian).

## Mode B: Change an existing vault's folders

Resolve config (Config Resolution Protocol in `llm-wiki/SKILL.md`) and read the vault's `AGENTS.md`. Law 9 applies: if `git status` shows changes you didn't make, stop and report.

**If `AGENTS.md` has no CATEGORIES table,** the vault uses the original seven folders. Add the table before changing anything, and show the user the diff first:

1. Insert a `## CATEGORIES` section after FOLDERS, copying the preamble from `$LLM_WIKI_REPO/presets/base/AGENTS.md`, with the table `llm-wiki layout <vault>` prints for the folders that exist: `| Folder | Holds | Role |`, one row per folder.
2. Change law 3 to: "Never write wiki pages outside the folders in the CATEGORIES table below."
3. Remove the category rows from the FOLDERS table and the old "Filing rule" line — the table replaces both.

**To add a folder:**

1. Add a row: the folder name (lowercase letters, digits, hyphens; never starting with `_` or `.`), what it holds, and a role only if it takes over a built-in part (rare — each role belongs to one folder). Put it above the general rows: rows are checked top-down, and the last row catches everything else.
2. Create the folder with an empty `.gitkeep`.
3. Add its page template to `_meta/templates/`. For a role's add-on folder, copy `$LLM_WIKI_REPO/presets/templates/<template>.md` (the add-on's template is named in `llm-wiki presets --json`, e.g. `meeting`, `course`). For a folder of the user's own, copy `presets/templates/page.md` and name it after the folder. Replace `__CATEGORY__` with the folder name and `__HOLDS__` with the row's Holds text.
4. Add a `## <Folder>` section to `index.md`.

**To rename or remove a folder:** only while it is empty. If it holds pages, stop and explain: moving pages changes their paths and `category:`, plus any path-style links and `.manifest.json` entries that point at them. That is its own planned operation, not part of setup.

**Then close it like any write operation** (DONE contract in `AGENTS.md`):

- `llm-wiki layout <vault>` shows the new table, `llm-wiki doctor --vault <vault>` passes, and `llm-wiki lint <vault> --json` has no fail-level findings.
- Append to `log.md`: `- [ISO-8601Z] LAYOUT agent=<agent> added=<folder>` (or `renamed=<old>><new>`, `removed=<folder>`).
- Note the change in `hot.md`, and commit: `wiki(layout): <summary>`.

## Optional: Other Settings

`llm-wiki setup` writes the essentials. Everything else is optional and documented under Environment Variables in `llm-wiki/SKILL.md`: `OBSIDIAN_SOURCES_DIR`, `CLAUDE_HISTORY_PATH`, `HERMES_HOME`, `OBSIDIAN_LINK_FORMAT`, `WIKI_TOKEN_WARN_THRESHOLD`, and the QMD variables. Ask about them only when the user brings them up.

## Optional: Install the Stop Hook (Auto-Capture)

Ask the user: **"Want to auto-capture findings at session end?"**

If yes, install the Stop hook into their global Claude Code settings so that every session
with meaningful work automatically prompts `/wiki-capture --quick` before closing.

**What the hook does:** reads the session transcript on Stop, counts file edits and shell
calls, and if significant work happened, asks Claude to run `/wiki-capture --quick` once.
The `wiki-capture` quick-mode KEEP/SKIP gate prevents noise — routine or
inconclusive sessions are skipped automatically.

**Installation steps:**

1. Find the llm-wiki repo path (the directory where this skill lives). If
   `LLM_WIKI_REPO` is set in `~/.llm-wiki/config`, use that. Otherwise run
   `llm-wiki info` to see the skills path, or ask the user. If the repo has no
   `.claude/hooks/wiki-stop-capture.sh`, this optional hook is not bundled —
   skip the install and tell the user.

2. Merge the hook entry into `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash <REPO_PATH>/.claude/hooks/wiki-stop-capture.sh"
          }
        ]
      }
    ]
  }
}
```

   If `~/.claude/settings.json` already exists and has a `hooks.Stop` array, **append** the new
   entry rather than replacing — don't clobber existing hooks.

3. Confirm: "Stop hook installed. Claude Code will prompt `/wiki-capture --quick` at the
   end of any session where you write files or run ≥ 4 shell commands."

**To uninstall later:** remove the hook entry from `~/.claude/settings.json` or set
`HIVEMIND_CAPTURE=false` in your shell to skip capture for a single session.

## Optional: Refresh QMD After Setup

If `QMD_WIKI_COLLECTION` is configured and the local QMD CLI is available, run `qmd update` after the initial vault files exist so the fresh vault is immediately queryable. No embedding pass is usually needed at setup time because the vault starts empty, so a plain update is enough unless you have already populated pages.

QMD is entirely optional and unset by default. Its configuration variables and procedures are documented in `llm-wiki/references/qmd.md`.
