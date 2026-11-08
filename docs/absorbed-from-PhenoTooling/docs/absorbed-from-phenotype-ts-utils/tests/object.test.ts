import { describe, it, expect } from 'vitest';
import { deepMerge, deepClone } from '../src/object.js';

describe('deepMerge', () => {
  it('merges simple objects', () => {
    const a = { x: 1, y: 2 };
    const b = { y: 3, z: 4 };
    expect(deepMerge(a, b)).toEqual({ x: 1, y: 3, z: 4 });
  });

  it('merges nested objects recursively', () => {
    const a = { x: { a: 1, b: 2 } };
    const b = { x: { b: 99, c: 3 } };
    expect(deepMerge(a, b)).toEqual({ x: { a: 1, b: 99, c: 3 } });
  });

  it('replaces arrays (does not concatenate)', () => {
    const a = { tags: ['a', 'b'] };
    const b = { tags: ['c'] };
    expect(deepMerge(a, b)).toEqual({ tags: ['c'] });
  });
});

describe('deepClone', () => {
  it('produces an independent copy', () => {
    const orig = { x: 1, nested: { y: 2 } };
    const copy = deepClone(orig);
    copy.nested.y = 99;
    expect(orig.nested.y).toBe(2);
  });
});
