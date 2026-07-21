# llm-wiki

Self-owned LLM wiki skills, helper CLI, and vault template for an Obsidian
knowledge vault. The skills live as real files in this repo (`skills/`), and
agent installs link to the repo checkout — never into site-packages — so a
`pip uninstall` or Python upgrade can never break installed skills.

## Install

```bash
git clone https://github.com/chobizzy/llm-wiki ~/Projects/llm-wiki
pip install -e ~/Projects/llm-wiki
llm-wiki setup --vault /path/to/your/vault
```

`setup` links every folder in `skills/` into each detected agent skills
directory (`~/.claude/skills/`, `~/.hermes/skills/`, …) and writes the global
config at `~/.llm-wiki/config`.

## Scaffold a new vault

`vault-template/` is a ready-to-copy vault skeleton: the constitution
(`AGENTS.md`), the seven page categories seeded with demo pages, `_meta/`
templates and hooks, and human docs. To start a new vault:

```bash
cp -r vault-template ~/Documents/my-wiki
cd ~/Documents/my-wiki
git init && git add -A && git commit -m "init: vault from template"
llm-wiki setup --vault .
```

See [vault-template/README.md](vault-template/README.md) for the full
quickstart and tour.

## Layout

```
llm_wiki/        helper CLI (stdlib-only, zero dependencies)
skills/          the skill folders — the actual product
vault-template/  ready-to-copy Obsidian vault skeleton
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

Config lives at `~/.llm-wiki/config` (flat `KEY="value"` lines).
