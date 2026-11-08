import { describe, it, expect } from 'vitest';
import { uniqueBy, groupBy } from '../src/array.js';

describe('uniqueBy', () => {
  it('deduplicates by the extracted key', () => {
    const items = [
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
      { id: 1, name: 'c' },
    ];
    expect(uniqueBy(items, (i) => i.id)).toEqual([
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
    ]);
  });

  it('preserves first-seen order', () => {
    const items = [3, 1, 2, 1, 3, 2];
    expect(uniqueBy(items, (x) => x)).toEqual([3, 1, 2]);
  });
});

describe('groupBy', () => {
  it('groups items into multiple buckets', () => {
    const items = [
      { type: 'a', v: 1 },
      { type: 'b', v: 2 },
      { type: 'a', v: 3 },
    ];
    expect(groupBy(items, (i) => i.type)).toEqual({
      a: [
        { type: 'a', v: 1 },
        { type: 'a', v: 3 },
      ],
      b: [{ type: 'b', v: 2 }],
    });
  });

  it('returns an empty object for empty input', () => {
    expect(groupBy([] as Array<{ k: string }>, (i) => i.k)).toEqual({});
  });
});
