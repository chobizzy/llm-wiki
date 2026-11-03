// Every hand-written string on the site. Facts that the repo already records (the laws, the
// DONE contract, the guide, the skill list, the vault graph) are read from the repo at build
// time by src/lib/vault.ts instead, so they cannot drift from it.
// No placeholders: every claim below paraphrases README.md or AGENTS.md.

export const site = {
  name: 'llm-wiki',
  url: 'https://chobizzy.github.io/llm-wiki/',
  repo: 'https://github.com/chobizzy/llm-wiki',
  tagline: 'Your notes, compiled.',
  description:
    'A knowledge base your AI agents maintain under written law. 31 skills, a zero-dependency Python CLI and an Obsidian vault governed by an 11-law constitution.',
  install: [
    'git clone https://github.com/chobizzy/llm-wiki ~/Projects/llm-wiki',
    'pip install -e ~/Projects/llm-wiki',
    'llm-wiki setup --vault /path/to/your/vault',
  ],
};

export const home = {
  lede: 'A knowledge base your AI agents maintain under written law. Not a chatbot, not a vector store: a folder of linked markdown pages you can read.',
  statement:
    'Most tools retrieve at question time: you ask, a retriever grabs some chunks, a model improvises, and nothing is learned. llm-wiki compiles once, when a source arrives. Your sources are the source code, your agents are the compiler, and the wiki is the build artifact.',
  specimen: {
    file: 'presets/demo/why-agents-need-a-constitution.md',
    notes: [
      { key: 'lifecycle: draft', text: 'Agents can only ever write draft. Promoting a page to reviewed is a line you edit by hand (law 10).' },
      { key: 'provenance', text: 'How much of the page came from sources, how much the model concluded, how much the sources dispute.' },
      { key: '^[inferred]', text: 'Ends any sentence the model concluded on its own. An unmarked sentence must paraphrase a real source (law 5).' },
      { key: '[[wikilinks]]', text: 'Written between related pages. They are the edges in the graph further down this page.' },
    ],
  },
  rag: [
    ['When work happens', 'At query time, every time', 'Once, at ingest. Reused after that'],
    ['What you get', 'An answer you cannot inspect', 'Pages you can read, edit and diff'],
    ['Storage', 'Vector DB, embeddings, an index', 'Plain files in a git repo'],
    ['Duplicates', 'Near-duplicate chunks pile up', 'One concept, one page (law 6)'],
    ['Hallucination', 'Invisible, mixed into prose', 'Marked inline: ^[inferred], ^[ambiguous]'],
    ['Trust', '“The model said so”', 'doctor and lint must pass'],
    ['Lock-in', 'Rebuild when the tool dies', 'A folder of markdown. Nothing to migrate'],
    ['API keys', 'Required', 'None. Your agent already has model access'],
  ],
  cli: [
    ['llm-wiki init <path>', 'Create a vault from a pack, roles and folders of your own'],
    ['llm-wiki setup --vault <path>', 'Link the skills into your agents and write the global config'],
    ['llm-wiki doctor', 'Health check: config, vault shape and layout, skill installs'],
    ['llm-wiki lint <path> --json', 'Frontmatter, broken links, lifecycle, duplicates, orphans'],
    ['llm-wiki graph-query', 'Answer structural questions from the link index alone'],
    ['llm-wiki layout', 'Show the vault’s folders and which one plays each role'],
  ],
};

// Grouping is editorial; membership is checked against skills/ at build time.
export const skillGroups: { name: string; note: string; skills: string[] }[] = [
  { name: 'Foundation', note: 'set up, switch and inspect vaults', skills: ['llm-wiki', 'wiki-setup', 'wiki-switch', 'wiki-status'] },
  { name: 'Ingest', note: 'turn sources and sessions into pages', skills: ['wiki-ingest', 'wiki-capture', 'wiki-update', 'wiki-import', 'wiki-research', 'wiki-history-ingest', 'claude-history-ingest', 'hermes-history-ingest', 'wiki-agent'] },
  { name: 'Read', note: 'answer from what is already compiled', skills: ['wiki-query', 'wiki-synthesize', 'wiki-digest', 'wiki-context-pack', 'wiki-export', 'memory-bridge'] },
  { name: 'Maintain', note: 'keep the vault honest over time', skills: ['wiki-lint', 'cross-linker', 'wiki-dedup', 'tag-taxonomy', 'daily-update', 'wiki-rebuild', 'wiki-stage-commit'] },
  { name: 'Obsidian', note: 'make the vault pleasant to browse', skills: ['wiki-dashboard', 'graph-colorize'] },
  { name: 'Meta', note: 'build and check more skills', skills: ['skill-creator', 'vault-skill-factory', 'impl-validator'] },
];

// One line per guide page for the home index. Keys must match guide/*.md (checked at build).
export const guideSummaries: Record<string, string> = {
  architecture: 'Three layers, the table that says where pages go, and the bookkeeping that keeps agents honest.',
  layouts: 'Two packs, six roles that combine, and folders of your own.',
  configuration: 'How the skills find your vault, and every CLI command in one table.',
  'multi-agent': 'Several agents, one vault: one constitution, tagged commits, git as the lock.',
  'maintenance-loops': 'From capture every session to the dream cycle every few weeks, and when to automate each loop.',
  'trust-and-provenance': 'Lifecycle, confidence, provenance and inline markers: four signals of how far to trust a page.',
};
