# Project site

The source of https://chobizzy.github.io/llm-wiki/. Astro, built into `../docs`, which GitHub
Pages serves from `main`.

```sh
npm install
npm run dev      # http://localhost:4321/llm-wiki/
npm run build    # writes ../docs (replaces its contents); commit it with the source
```

## Where the words come from

| On the site | Source |
|---|---|
| Guide pages | `../guide/*.md`, rendered as is (links to `x.md` become site routes) |
| The laws and the DONE contract | `../presets/base/AGENTS.md`, parsed at build time |
| Skill list and count | `../skills/*/SKILL.md`; groups in `src/data/site.ts` (the build fails if they drift) |
| The real vault graph | `src/data/vault-graph.svg`, written by `../scripts/graph-svg.py` |
| The link index in the corner | computed from this site's own links (`src/lib/vault.ts`) |
| Everything else | `src/data/site.ts` |

Adding a guide page: add the `.md` file, then its slug to `guideOrder` in `src/lib/vault.ts` and a
one-line summary to `guideSummaries` in `src/data/site.ts`. The build fails until all three agree.

Design decisions are in `DESIGN.md`.
