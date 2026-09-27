// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://tasken.phenotype.space',
  vite: {
    plugins: [tailwindcss()],
  },
});
