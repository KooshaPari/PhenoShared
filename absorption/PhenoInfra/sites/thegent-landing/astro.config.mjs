// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import { resolveSiteBase } from '../../packages/site-base/resolve-base.mjs';

export default defineConfig({
  site: 'https://thegent.kooshapari.com',
  base: resolveSiteBase('thegent-landing'),
  vite: {
    plugins: [tailwindcss()],
  },
});
