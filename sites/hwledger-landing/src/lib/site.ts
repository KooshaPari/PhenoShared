/**
 * Site path utilities for hwledger-landing
 */

import { SITE_CONFIG } from './constants';

/** Shared type — mirrors the upstream contract */
export type SitePathFunction = (path: string) => string;

/**
 * Constructs an absolute site path by prepending the base URL path.
 * @param path - The relative path to append
 * @returns The absolute path with base URL prefix
 */
export function sitePath(path: string): string {
  const base = SITE_CONFIG.baseUrl.endsWith('/') ? SITE_CONFIG.baseUrl : SITE_CONFIG.baseUrl + '/';
  return base + path.replace(/^\//, '');
}
