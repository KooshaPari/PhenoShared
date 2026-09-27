// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://khostty.phenotype.space',
  vite: {
    plugins: [tailwindcss()],
  },
});
