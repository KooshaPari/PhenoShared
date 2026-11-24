import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeSnapshot } from '../src/features/dispensary/data/adapters.ts';
import { latestItemsWithHistory } from '../src/features/dispensary/model/history.ts';
import { defaultFilters, defaultAssumptions, matches, money, perGram, plan, sortRows, summarize } from '../src/features/dispensary/model/catalog.ts';
const items = (raw: unknown[]) => latestItemsWithHistory([normalizeSnapshot({ date: '2026-10-09',
  stores: [{ slug: 'a', items: raw }] }, '2026-10-09')]);
test('filters keep unknowns without inventing medical access or gram weights', () => {
  const [unknown, low, volume] = items([{}, { name: 'Cart 1g', thc: 60 }, { name: 'Cart 1ml', thc: 90 }]);
  assert(matches(unknown, defaultFilters)); assert(!matches(low, defaultFilters));
  assert(matches(low, { ...defaultFilters, includeLowThc: true }));
  assert(!matches(unknown, { ...defaultFilters, access: 'medical' }));
  assert(!matches(volume, { ...defaultFilters, minSize: .5 }));
  assert(!matches(unknown, { ...defaultFilters, saleOnly: true }));
});
test('value summaries exclude missing prices, ml and explicitly absent menu entries', () => {
  const rows = items([{ name: 'Cart 1g' }, { name: 'Cart 1ml', after_tax: 1 },
    { name: 'Cart 1g', after_tax: 0, in_stock_on_menu: false }, { name: 'Cart 1g', after_tax: 10 }]);
  assert.equal(perGram(rows[0]), null); assert.equal(perGram(rows[1]), null); assert.equal(perGram(rows[2]), 0);
  assert.equal(summarize(rows).bestValue?.afterTax, 10); assert.equal(money(null), '—'); assert.equal(money(0), '$0.00');
});
test('sort is stable and places missing values last in both directions', () => {
  const rows = [{ id: 'a', n: null }, { id: 'b', n: 0 }, { id: 'c', n: 4 }, { id: 'd', n: 4 }];
  assert.deepEqual(sortRows(rows, r => r.n, 'asc').map(r => r.id), ['b', 'c', 'd', 'a']);
  assert.deepEqual(sortRows(rows, r => r.n, 'desc').map(r => r.id), ['c', 'd', 'b', 'a']);
});
test('scenario covers actual grams, honors cap, and does not divide by zero', () => {
  const rows = items([{ name: 'Cizi cart 0.5g', after_tax: 5 }, { name: 'Fallback cart 1g', after_tax: 20 }]);
  const result = plan(rows, { grams: 1.4, uplift: 0, target: 42, cap: 10 })!;
  assert.equal(result.watch[0].units, 2); assert.equal(result.watch[0].cover, 10);
  assert.equal(result.watch[0].bulkSpend, 14); assert.equal(result.fallback.length, 0);
  assert.equal(plan(rows, { ...defaultAssumptions, grams: 0 }), null);
  assert.equal(plan(rows, { ...defaultAssumptions, cap: NaN }), null);
  assert.equal(plan(items([{ name: 'Cizi cart 1g', after_tax: 0 }]), defaultAssumptions)!.watch[0].state, 'absent');
});
