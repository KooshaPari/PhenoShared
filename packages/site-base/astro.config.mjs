import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import { resolveSiteBase } from './resolve-base.mjs';

export default defineConfig({
  site: 'https://phenotype.space',
  base: resolveSiteBase('site-base'),
  integrations: [tailwind()],
});
