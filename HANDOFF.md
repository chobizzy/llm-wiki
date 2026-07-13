# HANDOFF — llm-wiki migration (2026-07-13)

## What this is
Self-owned replacement for the third-party `obsidian-wiki` pip package. The 32 vault
skills now live as real files in this repo (`skills/`); the stdlib-only helper CLI
(`llm_wiki/`) is installed editable (`pip install -e .`, user site). Agent skill dirs
symlink to this repo checkout — never to site-packages.

## State: Phases 1–4 DONE, Phase 5 PENDING VERDICT

Done and verified:
- Package scaffold + CLI (all obsidian-wiki subcommands kept; config at `~/.llm-wiki/`,
  legacy-config auto-migration, agent-dir existence gating, symlink→copy fallback).
  Fixed a latent bug: `batch.py` imported `obsidian_wiki.cache` inside a silent
  `except Exception` — unchanged-file skipping now actually works.
- 32 skills copied + rewritten (CLI calls → `llm-wiki`, config path → `~/.llm-wiki/`,
  `OBSIDIAN_WIKI_REPO` → `LLM_WIKI_REPO`, router trimmed to claude/hermes, dropped-skill
  references cleaned). Gate: 0 `obsidian-wiki` occurrences in `skills/`.
- Installed: 468 old site-packages links removed across 13 agent dirs; 6 empty scaffold
  dirs the old installer created were deleted (`~/.codex`, `~/.hermes`, `~/.openclaw`,
  `~/.trae`, `~/.trae-cn`, `~/.kiro`); `llm-wiki setup` linked 32 skills into the 7 real
  agent dirs (claude, gemini, antigravity, copilot, pi, .agents, Hermes AppData).
- Config migrated to `~/.llm-wiki/config` with all user keys preserved.
- Verified: `doctor` full pass; graph-analyse/graph-query/cache-check/cache-update-path/
  batch-plan/ast-extract all correct against the real vault; Claude Code live-loads the
  rewritten skills through the new links.

## Phase 5 (destructive — awaiting owner verdict)
1. `pip uninstall obsidian-wiki` (removes site-packages pkg + old exe)
2. Delete `~/.obsidian-wiki/` (legacy config, already migrated)

## Loose ends
- `llm-wiki.exe` was added to **user PATH** (`%APPDATA%\Python\Python314\Scripts`) —
  already-open terminals need a restart to see it.
- `daily-update`'s macOS launchd section references `$LLM_WIKI_REPO/scripts/…plist`;
  no such template is bundled (was never in the pip package either). Irrelevant on
  Windows; write the plist if ever needed on macOS.
- `wiki-setup`'s optional Stop-hook references `.claude/hooks/wiki-stop-capture.sh`,
  also never bundled; the skill now says to skip gracefully.
- Repo has no git remote yet (owner keeps repos private; add one for cross-machine reuse).
