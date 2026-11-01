# Layouts: packs, roles, and your own folders

*Which folders a vault has, and how to change them. Back to [architecture](architecture.md).*

## Two packs

`llm-wiki init PATH` creates a vault from a pack:

| Pack | Folders | What it is |
|---|---|---|
| **standard** (default) | `references/` `entities/` `synthesis/` `concepts/` | One folder per page type named in Karpathy's LLM-wiki gist: source summaries, entity pages, synthesis and comparisons, concept pages. |
| **minimal** | `wiki/` | The gist's single wiki directory. Each page's `category:` still names its kind (`references`, `entities`, `synthesis`, `concepts`), so `index.md` groups pages the way the gist's index does. |

In a terminal, `llm-wiki init` asks a few questions, shows the folder tree, and writes the vault when you confirm. Agents pass the answers as options instead (below). `llm-wiki presets` lists every choice.

## Roles add folders

On the standard pack, pick any roles — they combine:

| Role | Adds | For |
|---|---|---|
| `learner` | `courses/` | Courses, books, self-study: one hub page per course or book. |
| `researcher` | `questions/` | Papers and reports: one page per open question, with the current best answer. |
| `indie-hacker` | `projects/` | Building products: one overview page per project. Setup suggests importing your Claude Code history. |
| `creator` | `ideas/`, `outputs/` | Posts, videos, newsletters: content ideas, and what you shipped with the pages it used. |
| `team` | `meetings/`, `decisions/` | A shared wiki fed by meetings and chats. Setup suggests staged writes, so a human approves agent edits. |
| `personal` | `journal/` | Goals, health, reflections: one page per day. |

Why roles rather than more packs: people mix roles, and each one needs only a folder or two, so they stay small and combinable. Guides from people who pair Obsidian with AI agents agree on keeping the structure small on day one.

## Folders of your own

Add any folder when you create the vault (`--folder recipes="Cooking recipes: ingredients and steps"`), or later by editing the table. Names use lowercase letters, digits and hyphens, and can't start with `_` or `.`, which mark system folders.

## How filing works

The CATEGORIES table is in filing order: folders added by roles and folders of your own come first, then the pack's folders, and the pack's last row (`concepts/` or `wiki/`) catches everything else. An agent walks the rows top-down and uses the first whose *Holds* fits.

The *Role* column tells skills which folder plays a built-in part, so they work in any layout:

| Role | Standard folder | Written by |
|---|---|---|
| `reference` | `references/` | ingest (papers, URLs), capture, research |
| `entity` | `entities/` | ingest (code entities), history imports |
| `synthesis` | `synthesis/` | synthesize, research, lint consolidation |
| `concept` | `concepts/` | everything without a more specific home |
| `journal` | `journal/`, from the personal role | session captures, digests |
| `project` | `projects/`, from the indie-hacker role | history imports, ingest, update |
| `procedure` | `skills/`, only in vaults made before the table | history imports |

A role no row claims falls to the last row, and `llm-wiki layout --json` prints the resolved map. Without a project folder, skills record `project: <name>` in a page's frontmatter instead of nesting it.

## Changing the layout later

Edit the CATEGORIES table in `AGENTS.md`, then create the folder — or ask an agent ("add a recipes folder to my wiki"); the `wiki-setup` skill handles it, template and index section included. Rename or remove a folder only while it's empty. `llm-wiki doctor` warns about rows whose folder is missing, and `llm-wiki lint` fails on a malformed table.

Vaults created before the table keep the original seven folders (`journal/ projects/ references/ entities/ skills/ synthesis/ concepts/`) until a CATEGORIES table is added; nothing changes for them.

## For agents and scripts: init options

| Option | Meaning |
|---|---|
| `--pack NAME` | `standard` (default) or `minimal` |
| `--role NAME` | add a role's folders; repeatable |
| `--add NAME` | add one add-on folder: `meetings`, `decisions`, `journal`, `projects`, `courses`, `questions`, `ideas`, `outputs`; repeatable |
| `--folder NAME=HOLDS` | add a folder of your own; repeatable |
| `--rename OLD=NEW` | rename a folder |
| `--no-demo` | skip the five demo pages |
| `--backup-hook` | add a post-commit hook that pushes every commit to your remote |
| `--dry-run` | print the tree and CATEGORIES table without writing |
| `--yes` | never ask questions; use the options given |

Both packs, each role, and all roles together are tested to produce a vault with no fail-level lint findings, with and without demo pages.

*Next: [configuration](configuration.md)*
