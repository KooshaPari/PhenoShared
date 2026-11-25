/**
 * Site configuration for hwledger-landing
 */

export const SITE_CONFIG = {
  name: 'hwledger',
  displayName: 'HW Ledger',
  description: 'Hardware asset tracking and ledger management',
  primaryColor: '#3B82F6',
  accentColor: '#8B5CF6',
  baseUrl: import.meta.env.BASE_URL || '/',
  repo: 'KooshaPari/hwLedger',
} as const;

export type SiteConfig = typeof SITE_CONFIG;
