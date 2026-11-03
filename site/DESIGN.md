# llm-wiki project site: design record

## Brief

- **Subject:** llm-wiki, an open-source kit (31 agent skills, a zero-dependency Python CLI, an
  Obsidian vault template) that compiles sources into linked markdown pages under a written
  constitution.
- **Audience:** developers who already run Claude Code, Hermes or Codex and keep notes in
  Obsidian. They read docs, they distrust hype.
- **Job:** in 3 seconds say what it is; in 30 seconds make the "compiled, not retrieved" idea
  and the laws legible; then get them to clone it and read the guide.
- **Assets:** the repo itself (README, `guide/*.md`, `presets/base/AGENTS.md`, demo pages, the
  real vault graph in `src/data/vault-graph.svg`). The old AI-generated illustrations are
  dropped: they were decoration, and this concept's imagery is the link graph.
- **Constraints:** GitHub Pages serves `main:/docs` at `/llm-wiki/`, so Astro builds into
  `../docs` with `base: '/llm-wiki'`. No third-party requests.

## Phase 1: concepts

| | Idea | Anchor | Signature | O / F / Fe / P |
|---|---|---|---|---|
| A. Process | Reading the page is an ingest: the page moves from `_inbox/` through manifest, distill and gate | the real ingest pipeline | a source sheet advances through stages on scroll | 3 / 4 / 3 / 3 |
| B. Formal | The site is set as the constitution: numbered articles, every claim tagged extracted or inferred | AGENTS.md laws, law 5 markers | provenance markers resolve to the repo file they paraphrase | 4 / 4 / 3 / 2 |
| C. Material | **The docs are a vault.** Every page is a wiki page compiled from the repo's own markdown, and a live link index drawn from the site's real links shows where you are | the product's artifact is linked pages plus a link index (`graph-query` reads only that) | the link index: you are a lit node, hovering a link draws its edge, navigating sends the light down that edge | 4 / 5 / 4 / 2 |

**Pick C.** The site becomes an instance of the thing it describes, and the graph is real data
computed at build time, not an illustration. Steal from B for details: page frontmatter as the
hero meta, `^[inferred]` markers where the site itself infers, and the 404 as an archived page
(law 1: nothing is deleted).

## Concept card

```
Idea:        The docs are a vault: each page is a wiki page, and the link index shows where you are.
Metaphor:    an Obsidian vault seen through its own bookkeeping (frontmatter, wikilinks, index, lint).
Signature:   the persistent link index (#graph, transition:persist). Current page = lit node.
             Hovering any internal link draws the edge to its node. Navigating sends a spark
             along that edge while the page swaps underneath. On home the index starts large
             in the hero and docks into the corner as you scroll.
Emotion:     calm precision; "this thing keeps its own books".
Motion verb: link: a line draws from A to B, then the brackets close. Short, exact, no bounce.
Screenshot:  the home hero: "Your notes, compiled." at mega size beside the site's own graph,
             the home node lit, frontmatter keys hanging in the margin.
```

## Phase 2: system

**Palette** (paper and highlighter: a page you annotate, not a terminal)

| Role | Hex | Note |
|---|---|---|
| ground | `#F2F2EE` | cool paper, not cream |
| ink | `#121316` | text, graph edges |
| muted | `#585B63` | 6.1:1 on ground |
| line | `rgb(18 19 22 / 0.14)` | hairlines |
| accent | `#FFD83D` | highlighter. Only as a band behind ink or a node fill, never as text |
| curtain | `#121316` | transitions |

**Type**
- Archivo variable (wght 100 to 900, wdth 62 to 125), Google, OFL. Display at wdth 112 / wght
  760, tracking -0.045em, leading 0.86; text at wdth 100 / wght 400, 17 px, leading 1.55.
- JetBrains Mono 400 for markdown syntax only: frontmatter, `##` hashes hung in the margin,
  `[[ ]]` brackets, code. Mono is a syntax layer, not a label style.

**Grid & rhythm:** 12 columns, gutter `clamp(16px, 2.2vw, 40px)`. Three hang lines: col 1
(margin syntax), col 3 (text), col 8 (aside). Section padding moods: tight (8u), normal (16u),
airy (28u), viewport.

**Shape:** radius 0 everywhere, except graph nodes (circles).

**Motion language:** eases from the engine (`expo.out`, `expo.inOut`, `power3.out`). Edges draw
in 0.45 s; brackets close in 0.35 s; page transition 0.7 s each way. Big things slower.

**Micro-interactions (one per role)**
- Internal links, nav, CTAs-as-links: brackets `[[ ]]` travel in and the highlighter band
  rises, while the index draws the edge.
- Buttons (Copy): ink floods from the pointer side.
- Utility links (footer GitHub, license): underline only.

**Idle:** the link index breathes (each node drifts 1 to 2 px on the ticker) and leans slightly
toward the pointer. Off under reduced motion.

**Composition plan (home)**
```
1 Poster hero      [## frontmatter]  YOUR NOTES,          | graph (large)
                                     COMPILED.            |
                   lede · install block · [[Read the guide]]
2 Statement        8 cols, t-l: compiled once vs retrieved every time
3 Asymmetric pair  real page specimen (demo page, raw) 7 cols | notes on its markers 4 cols
4 Data             RAG vs llm-wiki table, full width
5 Index list       DONE contract: six rows that tick as you reach them
6 Gallery          the real vault graph (30 pages, 105 links) drawing itself on scroll
7 Two-column list  skills by group + CLI
8 Footer finale    install again, this site's own lint result, links
```
Guide pages: margin hashes, text on cols 3 to 9, frontmatter block at the top, prev/next as
wikilinks. Laws page: eleven laws as a numbered list set large.

**Genericness test:** a generic model would ship dark + mint accent + illustrations (the old
site, in fact) or a SaaS card grid. Changed: light paper ground with a highlighter, the graph
as the only image, markdown syntax as the typographic detail, the 404 as an archived page.

**Explainer figure:** the anatomy skill is installed, but the site's explainer IS the link
index (real data), so no isometric figure. Decision recorded.
