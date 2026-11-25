import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// The economics page keeps its logic inline in an <script is:inline> block, so
// these assertions read the shipped source rather than importing a module. That
// still catches a regression that removes the guard, and it fails loudly if the
// page is restructured, which is the point.
const page = readFileSync(new URL('../src/pages/economics/index.astro', import.meta.url), 'utf8');

test('API-supplied strings are escaped before reaching innerHTML', () => {
  // Every interpolation of API data must go through esc(). The assertions below
  // are the specific fields that were previously interpolated raw.
  for (const raw of [
    '${p.plan}',
    '${p.state}',
    '${p.effective}',
    "${p.notes || ''}",
    '${c.provider}',
    "${c.auth_type || ''}",
    '${c.total}',
    '${x.day}',
  ]) {
    assert.ok(
      !page.includes(raw),
      `raw interpolation still present: ${raw} — API values must be escaped`,
    );
  }
  assert.ok(page.includes('const esc = '), 'esc() helper is missing');
  // The cards interpolate through esc() rather than the bare identifier.
  assert.ok(page.includes('${esc(k)}'), 'top cards are not escaped');
  assert.ok(page.includes('${esc(p.plan)}'), 'plans table is not escaped');
  assert.ok(page.includes('${esc(c.provider)}'), 'fleet table is not escaped');
});

test('the 7-day figure is a calendar window, not a row slice', () => {
  // The original bug: daily rows arrive ORDER BY day DESC, so slice(0,7) took
  // the seven newest ROWS regardless of date and reported a September history as
  // a current 7-day total. The string "slice(0,7)" still appears in the comment
  // that documents the bug, so assert against executable code only.
  const code = page.replace(/^\s*\/\/.*$/gm, '');
  assert.ok(!/\(d\.daily\|\|\[\]\)\s*\.slice\(0, *7\)/.test(code), 'daily rows are still sliced');
  assert.ok(
    !/const reqs7 = [^;]*\.slice\(/.test(code),
    'reqs7 is still derived by slicing rows rather than filtering a window',
  );
  assert.ok(page.includes('windowStartKey'), 'no explicit window start');
  assert.ok(page.includes("timeZone: TZ"), 'window is not computed in a stated timezone');
  assert.ok(
    page.includes('x.day >= windowStartKey && x.day <= todayKey'),
    'rows are not filtered into the calendar window',
  );
});

test('a window with no rows is reported, not shown as a current total', () => {
  // A September-only history must not render as a live 7-day number.
  assert.ok(page.includes('windowHasData'), 'window emptiness is not tracked');
  assert.ok(
    page.includes("windowHasData ? String(reqs7) : '—'"),
    'an empty window still renders a numeric total',
  );
  assert.ok(page.includes('newest stored'), 'the newest stored day is not surfaced');
});

test('freshness reflects source data, never render time', () => {
  // The original bug: `updated ${new Date().toLocaleString()}` made a stale
  // snapshot look current.
  assert.ok(
    !page.includes("'updated ' + new Date()"),
    'status line still stamps render time as the update time',
  );
  assert.ok(page.includes('source data through'), 'source day is not reported');
  assert.ok(page.includes('rendered '), 'render time is not reported separately');
  assert.ok(page.includes('__econStale'), 'staleness is not tracked for the stamp');
  assert.ok(page.includes('STALE'), 'staleness is never surfaced to the reader');
});

test('the stamp prefers the server-derived latestDay when present', () => {
  // The API computes latestDay from the rows it returned, so the page should use
  // it rather than re-deriving it, while still working against an older endpoint.
  assert.ok(
    page.includes('d.latestDay ?? newestDay'),
    'page does not prefer the API latestDay with a fallback',
  );
});
