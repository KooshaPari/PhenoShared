import { describe, it, expect } from 'vitest';
import { cn, truncate, slugify } from '../src/string.js';

describe('cn', () => {
  it('concatenates class names and drops falsy', () => {
    expect(cn('a', 'b', 'c')).toBe('a b c');
    expect(cn('a', undefined, null, false, 'b')).toBe('a b');
    expect(cn()).toBe('');
  });
});

describe('truncate', () => {
  it('returns the string unchanged when within maxLen', () => {
    expect(truncate('hello', 10)).toBe('hello');
    expect(truncate('hello', 5)).toBe('hello');
  });

  it('truncates and appends suffix when too long', () => {
    expect(truncate('hello world', 8)).toBe('hello...');
  });

  it('throws when maxLen < len(suffix)', () => {
    expect(() => truncate('x', 2, '...')).toThrow();
  });

  it('honors custom suffix', () => {
    expect(truncate('abcdefghij', 7, '~')).toBe('abcdef~');
  });
});

describe('slugify', () => {
  it('converts basic strings', () => {
    expect(slugify('Hello World')).toBe('hello-world');
    expect(slugify('Foo & Bar')).toBe('foo-bar');
  });

  it('strips leading/trailing dashes', () => {
    expect(slugify('---foo---')).toBe('foo');
  });

  it('returns "untitled" for empty/all-special input', () => {
    expect(slugify('')).toBe('untitled');
    expect(slugify('!!!')).toBe('untitled');
  });
});
