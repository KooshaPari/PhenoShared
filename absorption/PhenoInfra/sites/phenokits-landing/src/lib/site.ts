/**
 * Site path utilities for phenokits-landing
 */

import { SITE_CONFIG } from './constants';

/**
 * Constructs an absolute site path by prepending the base URL path.
 * @param path - The relative path to append
 * @returns The absolute path with base URL prefix
 */
export function sitePath(path: string): string {
	const normalized = path.startsWith('/') ? path : `/${path}`;
	return `${SITE_CONFIG.baseUrl}${normalized}` || '/';
}
