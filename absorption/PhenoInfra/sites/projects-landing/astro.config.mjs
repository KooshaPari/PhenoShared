// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import { resolveSiteBase } from '../../packages/site-base/resolve-base.mjs';

// https://astro.build
export default defineConfig({
  site: 'https://projects.kooshapari.com',
  base: resolveSiteBase('projects-landing'),
  vite: {
    plugins: [tailwindcss()],
  },
});
