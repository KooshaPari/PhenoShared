// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://phenokits.kooshapari.com',
  base: process.env.GITHUB_PAGES === 'true' ? '/phenokits-landing' : '/',
  vite: {
    plugins: [tailwindcss()],
  },
});
