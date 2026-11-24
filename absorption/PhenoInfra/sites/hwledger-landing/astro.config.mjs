// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import { resolveSiteBase } from '../../packages/site-base/resolve-base.mjs';

export default defineConfig({
  site: 'https://hwledger.kooshapari.com',
  base: resolveSiteBase('hwledger-landing'),
  vite: {
    plugins: [tailwindcss()],
  },
});
