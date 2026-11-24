import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseHTML } from 'linkedom';

const html = readFileSync(new URL('../dist/index.html', import.meta.url), 'utf8');
const srcMatch = html.match(/<script type="module" src="(\/_astro\/[^"]+\.js)"/);
assert.ok(srcMatch, 'module script tag not found in dist/index.html');
const bundleURL = new URL('../dist' + srcMatch[1], import.meta.url).href;

const SNAP = { updated: '2026-10-15T12:00:00-07:00', dailyTarget: '3', writeups: [], applications: [
  { company: 'Acme', role: 'Eng', status: 'sent', date: '2026-10-14' },
] };
const flush = async () => { for (let i = 0; i < 4; i++) await new Promise(r => setImmediate(r)); };

let boots = 0;
async function boot(queue: Array<{ ok: boolean; status?: number }>) {
  const { document } = parseHTML(html);
  let fetches = 0, answerFetches = 0;
  const fetchStub = async (url: unknown) => {
    // The answers API fetch is a separate channel: it never drives the status
    // refetch timers this suite asserts on, so it gets its own counter.
    if (String(url).includes('/api/answers')) {
      answerFetches++;
      return { ok: true, status: 200, json: async () => ({ answers: [] }) };
    }
    const next = queue[Math.min(fetches, queue.length - 1)];
    fetches++;
    if (!next.ok) return { ok: false, status: next.status ?? 500, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => SNAP };
  };
  const timers: Array<{ ms: number; cb: () => void } | null> = [];
  const g = globalThis as Record<string, unknown>;
  g.document = document; g.window = { document }; g.self = g.window; g.location = { search: '' };
  g.fetch = fetchStub;
  g.setInterval = (cb: () => void, ms: number) => { timers.push({ ms, cb }); return timers.length; };
  g.clearInterval = (id: number) => { timers[id - 1] = null; };
  g.setTimeout = () => 0;
  g.clearTimeout = () => {};
  await import(bundleURL + '?boot=' + (++boots));
  const active = (ms: number) => timers.filter(t => t && t.ms === ms).length;
  const fire = async (ms: number) => { for (const t of [...timers]) if (t && t.ms === ms) t.cb(); await flush(); };
  return { document, fetches: () => fetches, answerFetches: () => answerFetches, active, fire };
}

test('initial fail -> manual Refresh success registers timers; data timer refetches', async () => {
  const { document, fetches, answerFetches, active, fire } = await boot([{ ok: false }, { ok: true }, { ok: true }]);
  await flush();
  assert.equal(fetches(), 1);
  assert.equal(active(300000), 0, 'no data timer before first successful fetch');
  assert.ok(document.getElementById('apps')?.textContent?.includes('Could not load'), 'initial error state missing');
  document.getElementById('refresh')?.click();
  await flush();
  assert.equal(fetches(), 2);
  assert.equal(answerFetches(), 1, 'successful refresh fetches answer history once');
  assert.ok(document.getElementById('apps')?.textContent?.includes('Acme'), 'data not rendered after refresh');
  assert.equal(active(300000), 1, 'exactly one data timer after recovery');
  assert.equal(active(60000), 1, 'exactly one label timer after recovery');
  await fire(60000);
  assert.equal(fetches(), 2, 'label timer must not fetch');
  assert.equal(answerFetches(), 1, 'label timer must not fetch answers');
  await fire(300000);
  assert.equal(fetches(), 3, 'data timer must drive exactly one refetch');
  assert.equal(answerFetches(), 2, 'data refresh fetches answer history separately');
});

test('initial fail -> Refresh fail shows Retry, never previous-snapshot; Retry success renders', async () => {
  const { document, fetches } = await boot([{ ok: false }, { ok: false }, { ok: true }]);
  await flush();
  document.getElementById('refresh')?.click();
  await flush();
  const upd = document.getElementById('updated')?.textContent ?? '';
  assert.ok(!upd.includes('previous snapshot'), 'first-ever failure must not claim a previous snapshot: ' + upd);
  assert.ok(document.getElementById('apps')?.textContent?.includes('Could not load'), 'error state missing after second failure');
  const retry = [...document.querySelectorAll('button')].find(b => b.textContent === 'Retry');
  assert.ok(retry, 'Retry button missing');
  retry!.click();
  await flush();
  assert.equal(fetches(), 3);
  assert.ok(document.getElementById('apps')?.textContent?.includes('Acme'), 'data not rendered after Retry');
});

test('repeated manual success does not stack timers', async () => {
  const { document, fetches, active, fire } = await boot([{ ok: true }, { ok: true }, { ok: true }, { ok: true }, { ok: true }]);
  await flush();
  for (let i = 0; i < 3; i++) { document.getElementById('refresh')?.click(); await flush(); }
  assert.equal(active(300000), 1, 'exactly one data timer after repeated refreshes');
  assert.equal(active(60000), 1, 'exactly one label timer after repeated refreshes');
  const before = fetches();
  await fire(300000);
  assert.equal(fetches(), before + 1, 'exactly one data refetch per interval');
});

test('silent failure after valid data preserves data and warns', async () => {
  const { document, fetches, fire } = await boot([{ ok: true }, { ok: false }]);
  await flush();
  assert.ok(document.getElementById('apps')?.textContent?.includes('Acme'));
  await fire(300000);
  assert.equal(fetches(), 2, 'silent refetch attempted');
  assert.ok(document.getElementById('apps')?.textContent?.includes('Acme'), 'previous snapshot must be preserved');
  assert.ok((document.getElementById('updated')?.textContent ?? '').includes('previous snapshot'), 'warning missing');
});
