# Configuration

## Config resolution

The wiki skills find your vault through the first match of:

1. An explicit `@name` vault override in your request (multi-vault setups; see the `wiki-switch` skill).
2. A local `.env` found by walking up from the working directory.
3. The global config at `~/.llm-wiki/config`.
4. If none exist, the agent runs the `wiki-setup` skill and interviews you.

`llm-wiki setup --vault /path/to/vault` writes the minimal global config (vault path, repo path, version) and links the skills into every detected agent. If the folder doesn't hold a vault yet, setup offers to create one, with the same questions as `llm-wiki init`. The config is flat `KEY="value"` lines; the optional keys (sources dir, history paths, staged writes, token thresholds) are documented in `skills/llm-wiki/SKILL.md`.

A vault's folders are not configuration. They live in the CATEGORIES table of its `AGENTS.md`, so they travel with the vault in git — see [layouts](layouts.md).

## The CLI in one minute

| Command | What it does |
|---|---|
| `llm-wiki init <path>` | Create a vault from a pack, roles, and folders of your own |
| `llm-wiki presets` | List the packs, roles, and add-on folders `init` can use |
| `llm-wiki layout [<path>]` | Show the vault's folders and which one plays each role |
| `llm-wiki setup --vault <path>` | Link skills into your agents + write global config |
| `llm-wiki doctor [--vault <path>] [--strict]` | Health check: config, vault shape and layout, skill installs |
| `llm-wiki lint <path> --json` | Frontmatter, broken links, lifecycle and layout errors, duplicates, orphans |
| `llm-wiki info` / `list` | Install paths and bundled skills |
| `llm-wiki graph-query` / `graph-analyse` / `query` | Answer from the wikilink graph; find god nodes and communities |
| `llm-wiki batch-plan` / `cache-check` / `cache-update` | Split big ingests into batches; track source hashes in `.manifest.json` |
| `llm-wiki ast-extract <path>` | Code structure (classes/functions/imports) without an LLM |

## Warnings

- **Don't move or delete the `llm-wiki` repo checkout.** Agent skill directories hold links into it, not copies — relocating it silently breaks every skill. If you must move it, re-run `llm-wiki setup` afterwards. (On filesystems without symlink support, `setup --copy` installs copies instead.)
- **Windows:** set `PYTHONUTF8=1` before running the CLI — its box-drawing output crashes legacy console codepages.

*Next: [multi-agent operation](multi-agent.md)*
