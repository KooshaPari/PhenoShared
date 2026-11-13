import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { parseHTML } from 'linkedom';

// These are behaviour tests, not source inspection: the page's own inline
// script is extracted from the BUILT artifact and executed against a real DOM
// with a real HTML parser, driven by API payloads a real deployment can return.
// A string-match test would pass while the escaping or the window maths was
// still wrong in the browser.

const DIST = new URL('../dist/economics/index.html', import.meta.url);
const distHtml = readFileSync(DIST, 'utf8');

const inlineScript = [...distHtml.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)]
  .map((m) => m[1])
  .find((s) => s.includes('innerHTML')) ?? '';

type Payload = {
  connections?: Record<string, unknown>[];
  plans?: Record<string, unknown>[];
  daily?: { day: string; requests: number }[];
  latestDay?: string | null;
  updated?: string;
  note?: string;
};

type Rendered = {
  doc: Document;
  topcards: string;
  status: string;
};

// Renders the built page against `data` and returns the resulting document.
async function render(data: Payload): Promise<Rendered> {
  const { document, window } = parseHTML(distHtml);
  const fetchStub = async () => ({ ok: true, json: async () => data });
  // Build a function whose parameters shadow any same-named globals, then call
  // it with this render's document/window/fetch.
  const page = new Function('document', 'window', 'fetch', inlineScript);
  page(document, window, fetchStub);
  await new Promise((r) => setTimeout(r, 50));
  return {
    doc: window.document,
    topcards: (window.document.querySelector('#topcards')?.textContent || '').replace(/\s+/g, ' ').trim(),
    status: (window.document.querySelector('#status')?.textContent || '').trim(),
  };
}

const EVIL = '<img src=x onerror="window.__PWNED=1">';

// The page keys its 7-day window in America/Los_Angeles (see index.astro).
// Tests that synthesize "today-relative" rows must use the same calendar, not
// UTC via Date#toISOString — near the UTC/LA day boundary those disagree and
// the fixture silently falls outside the real window.
const TZ = 'America/Los_Angeles';
const laDayKey = (d: Date = new Date()): string =>
  new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(d);
const laDayOffset = (back: number, from: Date = new Date()): string => {
  // Date-only arithmetic on the LA calendar key, matching the page's
  // windowStartKey construction (UTC midnight of y/m/d-back, then ISO date).
  const [y, m, dd] = laDayKey(from).split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, dd - back)).toISOString().slice(0, 10);
};

const emptyPayload = {
  connections: [],
  plans: [],
  daily: [],
  latestDay: null,
  updated: '',
  note: '',
};

test('the built page exposes an inline script and the cards container', async () => {
  // If the page is restructured, these fail loudly rather than silently
  // skipping every assertion below.
  assert.ok(inlineScript, 'no inline script found in the built page');
  assert.ok(parseHTML(distHtml).document.querySelector('#topcards'), '#topcards missing');
});

test('hostile API strings never become live markup', async () => {
  const payload = {
    ...emptyPayload,
    connections: [{ provider: EVIL, auth_type: EVIL, total: '1,000' }],
    plans: [{ plan: EVIL, state: EVIL, effective: EVIL, notes: EVIL }],
  };
  const { doc } = await render(payload);
  assert.equal(doc.querySelectorAll('img').length, 0, 'a raw <img> survived into the DOM');
  // The text must still be present, just inert.
  assert.ok(doc.body.textContent.includes('onerror'), 'payload text was dropped instead of escaped');
});

test('a stale history never renders as a live 7-day total', async () => {
  // The original issue #70 bug: rows are ordered by day DESC, so taking the
  // first 7 rows summed a September history (5+7+9 = 21) and reported it as the
  // current week. The window is empty here, so no number may be shown.
  const payload = {
    ...emptyPayload,
    daily: [
      { day: '2026-09-01', requests: 5 },
      { day: '2026-09-02', requests: 7 },
      { day: '2026-09-03', requests: 9 },
    ],
    latestDay: '2026-09-03',
    updated: '2026-09-03T00:00:00Z',
    note: 'stale',
  };
  const { topcards, status } = await render(payload);
    assert.ok(/Requests \(7d\)/.test(topcards), 'the 7-day card is missing');
    assert.ok(topcards.includes('—'), 'an empty window must render an em-dash, not a number');
    assert.ok(!topcards.includes('21'), 'stale rows were summed into a live total');
    assert.match(status, /STALE/, 'staleness was not surfaced to the reader');
  assert.match(status, /source data through 2026-09-03/, 'source day is not reported');
  assert.match(status, /rendered /, 'render time is not reported separately');
});

test('a genuine 7-day window still sums correctly', async () => {
  // Guards against over-correcting: the fix must not blank out real data.
  const daily = [];
  const today = new Date();
  for (let i = 0; i < 7; i += 1) {
    daily.push({ day: laDayOffset(i, today), requests: (i + 1) * 10 });
  }
  const sum = daily.reduce((a, x) => a + x.requests, 0);
  const { topcards, status } = await render({
    ...emptyPayload,
    daily,
    latestDay: daily[0].day,
    updated: today.toISOString(),
  });
  assert.ok(topcards.includes(String(sum)), `expected the real window total ${sum} in ${topcards}`);
  assert.ok(!topcards.includes('—'), 'a populated window must not render the empty-state dash');
  assert.doesNotMatch(status, /STALE/, 'fresh data was flagged stale');
});

test('a boundary-only window counts rows on the window edges', async () => {
  // Exactly six days back must be inside a seven-day window; eight days back
  // must not be. This is the off-by-one that a slice-based implementation hides.
  const mk = (back: number): { day: string; requests: number } => ({
    day: laDayOffset(back),
    requests: 1000,
  });
  const stamp = new Date().toISOString();
  const [inside, outside] = await Promise.all([
    render({ ...emptyPayload, daily: [mk(6)], latestDay: mk(6).day, updated: stamp }),
    render({ ...emptyPayload, daily: [mk(8)], latestDay: mk(8).day, updated: stamp }),
  ]);
  assert.ok(inside.topcards.includes('1000'), 'a row six days back is outside the 7-day window');
  assert.ok(outside.topcards.includes('—'), 'a row eight days back was counted inside the 7-day window');
});

test('stale rows never leak into a non-empty window', async () => {
  // Regression guard found by mutation testing. `reqs7` is rendered behind
  // `windowHasData`, so an EMPTY window masks a slicing bug completely. The
  // dangerous case is a window that has some real rows AND stale rows earlier in
  // a day-descending list: slice(0,7) then silently adds the ancient ones.
  // With the bug present this rendered 11034 instead of the correct 10999.
  const today = new Date();
  const daily = [
    { day: laDayOffset(0, today), requests: 9999 },
    { day: laDayOffset(2, today), requests: 1000 },
    { day: '2026-01-05', requests: 7 },
    { day: '2026-01-04', requests: 7 },
    { day: '2026-01-03', requests: 7 },
    { day: '2026-01-02', requests: 7 },
    { day: '2026-01-01', requests: 7 },
  ];
  const { topcards } = await render({
    ...emptyPayload,
    daily,
    latestDay: laDayOffset(0, today),
    updated: today.toISOString(),
  });
  assert.ok(topcards.includes('10999'), `expected only in-window rows (10999), got: ${topcards}`);
  assert.ok(!topcards.includes('11034'), 'stale rows leaked into the window total');
});

test('a totally empty payload degrades without throwing', async () => {
  const { topcards } = await render(emptyPayload);
  assert.ok(/Requests \(7d\)/.test(topcards), 'the card should still render with no data at all');
  assert.ok(topcards.includes('—'), 'no data must render as unknown');
});

// Regression: #68 merged with the calendar window computing UTC midnight for
// today-minus-6 and FORMATTING it in America/Los_Angeles, which reads a UTC
// midnight as the previous LA evening and shifts the window start back a day.
test('calendar window covers exactly the last 7 LA dates around Oct 15', async () => {
  const RealDate = Date;
  class FixedDate extends RealDate {
    constructor(...args: any[]) {
      super(...((args.length ? args : ['2026-10-15T20:00:00Z']) as [string])); // Thu Oct 15, 1 PM in LA
    }
  }
  (globalThis as any).Date = FixedDate;
  try {
    const daily = [];
    for (let i = 6; i >= 0; i--) daily.push({ day: `2026-10-${String(15 - i).padStart(2, '0')}`, requests: 100 });
    daily.push({ day: '2026-10-08', requests: 5000 }); // one day before the window
    const { topcards } = await render({ ...emptyPayload, daily, latestDay: '2026-10-15', updated: '2026-10-15T20:00:00Z' });
    assert.ok(topcards.includes('700'), `expected the 7 in-window rows (700), got: ${topcards}`);
    assert.ok(!topcards.includes('5700'), 'the pre-window row 2026-10-08 leaked into the total');
    assert.ok(topcards.includes('2026-10-09 to 2026-10-15'), `window label wrong: ${topcards}`);
  } finally {
    (globalThis as any).Date = RealDate;
  }
});

test('calendar window start survives month, year and DST boundaries', async () => {
  const RealDate = Date;
  const cases: [string, string][] = [
    ['2026-11-01T20:00:00Z', '2026-10-26'], // month boundary; also DST-end day in LA
    ['2027-01-01T20:00:00Z', '2026-12-26'], // year boundary
    ['2026-03-08T20:00:00Z', '2026-03-02'], // DST-start day in LA
  ];
  for (const [now, expectStart] of cases) {
    class FixedDate extends RealDate {
      constructor(...args: any[]) {
        super(...((args.length ? args : [now]) as [string]));
      }
    }
    (globalThis as any).Date = FixedDate;
    try {
      const { topcards } = await render({ ...emptyPayload, daily: [{ day: expectStart, requests: 42 }], latestDay: expectStart, updated: now });
      assert.ok(topcards.includes(expectStart), `at ${now}: expected a window starting ${expectStart}, got: ${topcards}`);
      assert.ok(topcards.includes('42'), `at ${now}: the boundary-day row fell out of the window`);
    } finally {
      (globalThis as any).Date = RealDate;
    }
  }
});

// Regression: #68 rendered numeric c.active as a truthiness-coerced 1/0,
// collapsing real provider counts (11 -> 1). Counts render verbatim after
// validation; invalid, negative or markup-bearing values render as unknown.
test('fleet counts render validated numbers, never truthiness coercions', async () => {
  const { doc, topcards } = await render({
    ...emptyPayload,
    connections: [
      { provider: 'p0', auth_type: 'key', active: 0, total: 4 },
      { provider: 'p1', auth_type: 'key', active: 1, total: 4 },
      { provider: 'p4', auth_type: 'key', active: 4, total: 8 },
      { provider: 'p8', auth_type: 'key', active: 8, total: 8 },
      { provider: 'p11', auth_type: 'key', active: 11, total: 16 },
      { provider: 'bad-neg', auth_type: 'key', active: -3, total: 2 },
      { provider: 'bad-str', auth_type: 'key', active: '8<script>alert(1)</script>', total: '<img src=x onerror=alert(1)>' },
    ],
  });
  const fleet = (doc.querySelector('#fleet tbody') as unknown as HTMLElement).innerHTML;
  for (const cell of ['>0<', '>1<', '>4<', '>8<', '>11<']) assert.ok(fleet.includes(cell), `missing count ${cell} in ${fleet}`);
  assert.ok(!fleet.includes('alert('), 'markup reached the fleet table');
  assert.match(fleet, /unknown/, 'invalid or negative counts must render as unknown');
  assert.ok(topcards.includes('24'), `top-card sum must use validated counts (0+1+4+8+11=24), got: ${topcards}`);
});
