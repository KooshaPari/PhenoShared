import { describe, it, expect } from 'vitest';
import { formatDate, parseDate, addDays } from '../src/date.js';

describe('formatDate', () => {
  const d = new Date(Date.UTC(2025, 5, 15, 12, 0, 0));

  it('formats as ISO YYYY-MM-DD by default', () => {
    expect(formatDate(d)).toBe('2025-06-15');
  });

  it('formats as US MM/DD/YYYY', () => {
    expect(formatDate(d, 'us')).toBe('06/15/2025');
  });

  it('formats as EU DD/MM/YYYY', () => {
    expect(formatDate(d, 'eu')).toBe('15/06/2025');
  });
});

describe('parseDate', () => {
  it('parses a valid ISO 8601 string', () => {
    const d = parseDate('2025-06-15T00:00:00Z');
    expect(d).toBeInstanceOf(Date);
    expect(d!.getUTCFullYear()).toBe(2025);
  });

  it('returns null on invalid input', () => {
    expect(parseDate('not-a-date')).toBeNull();
  });
});

describe('addDays', () => {
  it('adds positive days', () => {
    const d = new Date(Date.UTC(2025, 0, 1));
    const r = addDays(d, 5);
    expect(r.getUTCDate()).toBe(6);
  });

  it('subtracts with negative days', () => {
    const d = new Date(Date.UTC(2025, 0, 10));
    const r = addDays(d, -3);
    expect(r.getUTCDate()).toBe(7);
  });
});
