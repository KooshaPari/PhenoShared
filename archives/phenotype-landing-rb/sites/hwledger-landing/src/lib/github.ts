/**
 * GitHub API utilities for hwledger-landing
 */

import type { GhRepoMeta, GhRelease } from './types';
import { SITE_CONFIG } from './constants';

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

const USER_AGENT = 'hwledger-landing-build';

/**
 * Fetch from GitHub API with automatic token handling and error fallback.
 * @param path - API path (e.g., 'repos/KooshaPari/hwLedger')
 * @param accept - Accept header media type
 * @returns Parsed JSON/text response or null on failure
 */
export async function gh<T = unknown>(
  path: string,
  accept = 'application/vnd.github+json',
): Promise<T | null> {
  try {
    const res = await fetch(`https://api.github.com/${path}`, {
      headers: {
        Accept: accept,
        'User-Agent': USER_AGENT,
        ...(GITHUB_TOKEN ? { Authorization: `Bearer ${GITHUB_TOKEN}` } : {}),
      },
    });
    if (!res.ok) {
      console.warn(`[github] ${path} -> ${res.status}; falling back to snapshot`);
      return null;
    }
    return (accept.includes('html') ? await res.text() : await res.json()) as T;
  } catch (err) {
    console.warn(`[github] ${path} fetch failed: ${(err as Error).message}; falling back to snapshot`);
    return null;
  }
}

/**
 * Fetch repository metadata from GitHub API.
 */
export async function fetchRepoMeta(): Promise<GhRepoMeta | null> {
  return gh<GhRepoMeta>(`repos/${SITE_CONFIG.repo}`);
}

/**
 * Fetch repository releases from GitHub API.
 */
export async function fetchReleases(perPage = 5): Promise<GhRelease[]> {
  const result = await gh<GhRelease[]>(
    `repos/${SITE_CONFIG.repo}/releases?per_page=${perPage}`,
  );
  return result ?? [];
}

/**
 * Fetch JSON from GitHub API (helper for page components).
 */
export async function ghJson<T = unknown>(path: string): Promise<T | null> {
  return gh<T>(path, 'application/vnd.github+json');
}

/**
 * Fetch raw content from GitHub API.
 */
export async function ghRaw(path: string): Promise<string | null> {
  return gh<string>(path, 'application/vnd.github.raw');
}

/**
 * Fetch HTML content from GitHub API.
 */
export async function ghHtml(path: string): Promise<string | null> {
  return gh<string>(path, 'application/vnd.github.html+json');
}
