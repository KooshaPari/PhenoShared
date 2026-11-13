import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import legacyAliases from './scripts/legacy-aliases.mjs';

export default defineConfig({
  output: 'static',
  publicDir: './.staged/public',
  outDir: './dist',
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [react(), legacyAliases()],
  vite: { plugins: [tailwindcss()] },
});
