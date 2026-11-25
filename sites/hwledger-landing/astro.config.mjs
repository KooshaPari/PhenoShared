// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import { resolveSiteBase } from '../../packages/site-base/resolve-base.mjs';

export default defineConfig({
  site: 'https://hwledger.<REDACTED>.com',
  base: resolveSiteBase('hwledger-landing'),
  vite: {
    plugins: [tailwindcss()],
  },
});
