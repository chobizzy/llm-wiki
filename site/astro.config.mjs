// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { unified } from '@astrojs/markdown-remark';
import rehypeGuide from './src/lib/rehype-guide.mjs';

// GitHub Pages serves main:/docs at https://chobizzy.github.io/llm-wiki/, so the build
// writes straight into ../docs. `npm run build` replaces that folder's contents.
const base = '/llm-wiki/';

export default defineConfig({
  site: 'https://chobizzy.github.io',
  base,
  trailingSlash: 'always',
  outDir: '../docs',
  integrations: [sitemap({ filter: (page) => !page.includes('/og/') })],
  prefetch: { prefetchAll: true, defaultStrategy: 'hover' },
  build: { inlineStylesheets: 'always' },
  markdown: { processor: unified({ rehypePlugins: [[rehypeGuide, { base }]] }), syntaxHighlight: false },
});
