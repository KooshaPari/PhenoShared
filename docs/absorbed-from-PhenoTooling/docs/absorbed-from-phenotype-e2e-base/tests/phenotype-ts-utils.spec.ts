/**
 * phenotype-ts-utils adoption smoke test.
 *
 * Verifies that the `phenotype-ts-utils` library is importable from
 * the e2e-base Playwright test suite. The import is a tree-shakeable
 * ESM module, so it works equally in Node and Playwright contexts.
 *
 * See https://github.com/KooshaPari/phenotype-ts-utils/releases/tag/v0.1.0
 */
import { test, expect } from '@playwright/test';
import { cn, truncate, formatDate, deepMerge, uniqueBy } from 'phenotype-ts-utils';

test.describe('phenotype-ts-utils adoption', () => {
  test('cn joins and drops falsy class names', () => {
    expect(cn('a', 'b', 'c')).toBe('a b c');
    expect(cn('btn', undefined, null, false, 'is-active')).toBe('btn is-active');
  });

  test('truncate caps a long string with default suffix', () => {
    expect(truncate('a'.repeat(100), 10)).toBe('aaaaaaa...');
  });

  test('formatDate renders ISO YYYY-MM-DD', () => {
    const d = new Date(Date.UTC(2025, 0, 1));
    expect(formatDate(d)).toBe('2025-01-01');
  });

  test('deepMerge merges nested objects', () => {
    const a = { fixtures: { base: 'http://localhost:3000', timeout: 5000 } };
    const b = { fixtures: { timeout: 10000 } };
    expect(deepMerge(a, b)).toEqual({
      fixtures: { base: 'http://localhost:3000', timeout: 10000 },
    });
  });

  test('uniqueBy dedupes fixture entries by URL', () => {
    const fixtures = [
      { url: '/', name: 'home' },
      { url: '/about', name: 'about' },
      { url: '/', name: 'home-2' },
    ];
    expect(uniqueBy(fixtures, (f) => f.url)).toEqual([
      { url: '/', name: 'home' },
      { url: '/about', name: 'about' },
    ]);
  });
});
