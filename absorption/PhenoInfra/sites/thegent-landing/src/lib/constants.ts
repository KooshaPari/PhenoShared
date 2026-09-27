/**
 * Site configuration for thegent-landing
 */

export const SITE_CONFIG = {
  name: 'thegent',
  displayName: 'TheGent',
  description: 'AI-powered development agent toolkit',
  primaryColor: '#F59E0B',
  accentColor: '#EF4444',
  baseUrl: import.meta.env.BASE_URL || '/',
} as const;

/**
 * Base path for all site routes.
 * Derived from the site's base URL at build time.
 */
export const BASE_PATH = SITE_CONFIG.baseUrl.replace(/\/$/, '') || '/';

export type SiteConfig = typeof SITE_CONFIG;
