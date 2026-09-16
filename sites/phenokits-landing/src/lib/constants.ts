/**
 * Site configuration for phenokits-landing
 */

export const SITE_CONFIG = {
  name: 'phenokits',
  displayName: 'PhenoKits',
  description: 'Production-ready solution kits and bundles',
  primaryColor: '#10B981',
  accentColor: '#3B82F6',
  baseUrl: import.meta.env.BASE_URL || '/',
} as const;

export type SiteConfig = typeof SITE_CONFIG;
