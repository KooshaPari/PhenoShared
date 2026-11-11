/**
 * phenotype-ts-utils adoption smoke tests.
 *
 * Verifies that the @phenotype/auth-ts repo can import and use the
 * shared `phenotype-ts-utils` library. These are intentionally simple —
 * the real value is in (a) the dep-resolves-cleanly guarantee and
 * (b) showing other repos that the integration is straightforward.
 *
 * See https://github.com/KooshaPari/phenotype-ts-utils/releases/tag/v0.1.0
 */
import { describe, expect, it } from 'vitest';
import {
  cn,
  truncate,
  formatDate,
  deepMerge,
  uniqueBy,
  groupBy,
} from 'phenotype-ts-utils';

describe('phenotype-ts-utils: cn', () => {
  it('joins truthy class names and drops falsy', () => {
    expect(cn('a', 'b', 'c')).toBe('a b c');
    expect(cn('btn', undefined, null, false, 'is-active')).toBe('btn is-active');
  });
});

describe('phenotype-ts-utils: truncate', () => {
  it('truncates a long string with default suffix', () => {
    expect(truncate('a'.repeat(100), 10)).toBe('aaaaaaa...');
  });

  it('returns input unchanged when within maxLen', () => {
    expect(truncate('short', 80)).toBe('short');
  });
});

describe('phenotype-ts-utils: formatDate', () => {
  it('formats a Date as ISO by default', () => {
    const d = new Date(Date.UTC(2025, 5, 15, 0, 0, 0));
    expect(formatDate(d)).toBe('2025-06-15');
  });
});

describe('phenotype-ts-utils: deepMerge', () => {
  it('merges nested objects recursively', () => {
    const a = { jwt: { alg: 'HS256', ttl: 3600 } };
    const b = { jwt: { alg: 'RS256', aud: 'phenotype' } };
    expect(deepMerge(a, b)).toEqual({
      jwt: { alg: 'RS256', ttl: 3600, aud: 'phenotype' },
    });
  });
});

describe('phenotype-ts-utils: array helpers', () => {
  it('uniqueBy dedupes by a key', () => {
    const tokens = [
      { id: 'a', scope: 'read' },
      { id: 'b', scope: 'write' },
      { id: 'a', scope: 'admin' },
    ];
    expect(uniqueBy(tokens, (t) => t.id)).toEqual([
      { id: 'a', scope: 'read' },
      { id: 'b', scope: 'write' },
    ]);
  });

  it('groupBy buckets by a key', () => {
    const items = [
      { scope: 'read', v: 1 },
      { scope: 'write', v: 2 },
      { scope: 'read', v: 3 },
    ];
    expect(groupBy(items, (i) => i.scope)).toEqual({
      read: [
        { scope: 'read', v: 1 },
        { scope: 'read', v: 3 },
      ],
      write: [{ scope: 'write', v: 2 }],
    });
  });
});
