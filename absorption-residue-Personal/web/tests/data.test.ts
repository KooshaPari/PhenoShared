import { test } from 'node:test';
import assert from 'node:assert/strict';
import { number, date } from '../src/features/dispensary/data/primitives.ts';
import { normalizeSnapshot, normalizeManual, normalizeCadence, normalizeDeals } from '../src/features/dispensary/data/adapters.ts';
import { latestItemsWithHistory } from '../src/features/dispensary/model/history.ts';
import { loadDispensary } from '../src/features/dispensary/data/load.ts';

test('missing fields stay unknown; raw data and manual wrapper survive', () => {
  for (const value of [null, false, true, '', ' ', {}, [], Infinity]) assert.equal(number(value), null);
  assert.equal(number('0'), 0); assert.equal(date('2026-02-30'), null);
  const raw = { stores: [null, { items: [null, {}, { name: 'Cart 0.5ml', thc: '400', extra: 'kept' }] }] };
  const snapshot = normalizeSnapshot(raw, '2026-10-09');
  assert.equal(snapshot.raw, raw); assert.equal(snapshot.dateInferred, true);
  assert.equal(snapshot.stores[0].items[0].menuListed, null);
  assert.equal(snapshot.stores[0].items[0].listed, null);
  assert.equal(snapshot.stores[0].items[1].volumeSize, true);
  assert.equal(snapshot.stores[0].items[1].raw.extra, 'kept');
  assert.equal(snapshot.halfValue.available, false);
  assert.equal(normalizeManual({ entries: [null, { price: '0' }] })[0].price, 0);
  assert.equal(normalizeCadence({ brands: { 'a|b': {} } }).brands[0].gaps, null);
  assert.deepEqual(normalizeDeals({ stores: { a: [{ recurring: true }] } }).deals[0].weekdays, Array(7).fill(null));
});
test('display-name changes match; duplicate matches suppress drop claims', () => {
  const snap = (d: string, listed: number, count = 1) => normalizeSnapshot({ date: d, stores: [{ slug: 'a', listing: { name: d },
    items: Array.from({ length: count }, () => ({ name: 'Cart 1g', brand: 'B', listed, original: 30 })) }] }, d);
  const rows = latestItemsWithHistory([snap('2026-10-08', 20), snap('2026-10-09', 15)]);
  assert.equal(rows[0].comparison.drop, 5); assert.equal(rows[0].comparison.state, 'matched');
  assert.equal(rows[0].discountPercent, 50);
  const ambiguous = latestItemsWithHistory([snap('2026-10-08', 20, 2), snap('2026-10-09', 15)]);
  assert.equal(ambiguous[0].comparison.state, 'ambiguous'); assert.equal(ambiguous[0].comparison.drop, null);
});
test('fixed URLs, partial failures, last-14 window and snapshot concurrency', async () => {
  const calls: string[] = []; let active = 0, peak = 0;
  const fetcher: typeof fetch = async (input, init) => {
    const url = String(input); calls.push(url); assert.equal(init?.cache, 'no-store');
    if (url.endsWith('manifest.json')) return new Response(JSON.stringify({ dates: Array.from({ length: 16 }, (_, i) => `2026-10-${String(i + 1).padStart(2, '0')}`) }));
    if (url.endsWith('cadence.json')) return new Response('', { status: 404 });
    if (url.endsWith('deal_patterns.json')) return new Response('<html>fallback</html>');
    if (url.includes('/snapshots/')) {
      peak = Math.max(peak, ++active); await new Promise(r => setTimeout(r, 2)); active--;
      return new Response(JSON.stringify({ date: url.slice(-15, -5), stores: [] }));
    }
    return new Response(url.endsWith('manual.json') ? '[]' : '{}');
  };
  const result = await loadDispensary({ fetcher });
  assert.equal(result.snapshots.length, 14); assert.equal(result.sources.cadence.state, 'missing');
  assert.equal(result.sources.deals.state, 'error'); assert(peak <= 4);
  assert(calls.every(url => url.startsWith('/dispensary/data/')));
  assert(!calls.some(url => url.includes('2026-10-01.json')));
});
test('caller cancellation rejects, request timeouts remain partial errors', async () => {
  const fetcher: typeof fetch = async (_, init) => new Promise((_, reject) => {
    init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
  });
  const controller = new AbortController();
  const pending = loadDispensary({ signal: controller.signal, fetcher }); controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  const timed = await loadDispensary({ timeoutMs: 5, fetcher });
  assert.equal(timed.sources.manifest.state, 'error'); assert.equal(timed.sources.manifest.error, 'Request timed out');
});
