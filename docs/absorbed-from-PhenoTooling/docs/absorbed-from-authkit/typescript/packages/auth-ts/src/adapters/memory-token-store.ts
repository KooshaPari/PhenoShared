/**
 * In-memory TokenStore for tests and dev.
 */

import type { Token } from '../domain/token';
import type { TokenStore } from '../ports';

type Entry = { token: unknown; expiryMs: number };

export class MemoryTokenStore implements TokenStore {
  private readonly data = new Map<string, Entry>();

  async save(key: string, token: unknown, ttlSeconds: number): Promise<void> {
    const expiryMs = Date.now() + ttlSeconds * 1000;
    this.data.set(key, { token, expiryMs });
  }

  async get(key: string): Promise<unknown | null> {
    const entry = this.data.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiryMs) {
      this.data.delete(key);
      return null;
    }
    return entry.token;
  }

  async delete(key: string): Promise<void> {
    this.data.delete(key);
  }
}

/** Narrow unknown to Token when callers expect it. */
export function asToken(value: unknown): Token | null {
  if (!value || typeof value !== 'object') return null;
  const o = value as Record<string, unknown>;
  if (typeof o.accessToken !== 'string' || typeof o.tokenType !== 'string') return null;
  return value as Token;
}
