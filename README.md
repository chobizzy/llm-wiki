# llm-wiki

Self-owned LLM wiki skills and helper CLI for an Obsidian knowledge vault.
Replaces the third-party `obsidian-wiki` pip package: the skills live as real
files in this repo (`skills/`), and agent installs link to the repo checkout —
never into site-packages — so a `pip uninstall` or Python upgrade can never
break installed skills.

## Install

```bash
git clone <this-repo> ~/Projects/llm-wiki
pip install -e ~/Projects/llm-wiki
llm-wiki setup --vault /path/to/your/vault
```

`setup` links every folder in `skills/` into each detected agent skills
directory (`~/.claude/skills/`, `~/.hermes/skills/`, …) and writes the global
config at `~/.llm-wiki/config`.

## Layout

```
llm_wiki/     helper CLI (stdlib-only, zero dependencies)
skills/       the skill folders — the actual product
```

## CLI

| Command | Purpose |
|---|---|
| `llm-wiki setup [--vault PATH] [--copy]` | link skills into agents, write config |
| `llm-wiki list` / `llm-wiki info` | list skills / show install status |
| `llm-wiki doctor [--strict] [--json]` | health-check config, vault, installs |
| `llm-wiki graph-analyse VAULT` | god nodes, communities, surprising connections |
| `llm-wiki graph-query VAULT "question"` | answer from the wikilink index, no page reads |
| `llm-wiki query "question"` | graph-query against the configured vault |
| `llm-wiki batch-plan VAULT SRC_DIR` | split sources into parallel-ingest batches |
| `llm-wiki cache-check VAULT SRC...` | new/modified/unchanged vs `.manifest.json` |
| `llm-wiki cache-update VAULT SRC --pages ...` | record ingest hash in the manifest |
| `llm-wiki cache-hash PATH` | SHA-256 of a file or directory |
| `llm-wiki ast-extract PATH` | code structure (classes/functions/imports), no LLM |
| `llm-wiki lint [VAULT]` | frontmatter, broken links, duplicates, orphans |

Config lives at `~/.llm-wiki/config` (flat `KEY="value"` lines). On first
`setup`, values are migrated from a legacy `~/.obsidian-wiki/config` if one
exists.
