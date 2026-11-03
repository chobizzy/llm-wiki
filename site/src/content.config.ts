import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';

// The repo's own guide/ folder is the source of the guide pages.
export const collections = {
  guide: defineCollection({ loader: glob({ pattern: '*.md', base: '../guide' }) }),
};
