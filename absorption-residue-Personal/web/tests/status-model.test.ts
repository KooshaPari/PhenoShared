import { test } from 'node:test';
import assert from 'node:assert/strict';
import { staleness, missedGaps, sparkline, diffRows, filterRows, toCSV, toJSON, type StatusRow } from '../src/features/status/model.ts';

const r = (o: Partial<StatusRow>): StatusRow => ({ id: 1, project: 'P', project_id: null, status: 'active', percent: 10, unknown_cause: null, start_step: null, text: 't', recorded_at: '2026-10-22T08:00:00.000Z', source_label: 'Dot-reported, unverified', verified: false, ...o });
const now = new Date('2026-10-22T09:00:00.000Z');

test('staleness badge follows the 30-minute cadence', () => {
  assert.equal(staleness('2026-10-22T08:45:00.000Z', now).state, 'fresh');
  assert.equal(staleness('2026-10-22T08:10:00.000Z', now).state, 'late');
  const s = staleness('2026-10-22T06:00:00.000Z', now);
  assert.equal(s.state, 'stale');
  assert.match(s.label, /updates missed/);
  assert.equal(staleness(null, now).state, 'unknown');
  assert.equal(staleness('garbage', now).state, 'unknown');
});

test('missed-update gaps count only gaps wider than two cadences', () => {
  const g = missedGaps(['2026-10-22T08:00:00Z', '2026-10-22T08:30:00Z', '2026-10-22T10:00:00Z', null]);
  assert.equal(g.count, 1);
  assert.equal(g.gaps[0].minutes, 90);
});

test('sparkline uses measured values only and never zero-fills unknowns', () => {
  const rows = [r({ id: 1, percent: 10, recorded_at: '2026-10-22T08:00:00Z' }), r({ id: 2, percent: null, recorded_at: '2026-10-22T08:30:00Z' }), r({ id: 3, percent: 50, recorded_at: '2026-10-22T09:00:00Z' })];
  const s = sparkline(rows);
  assert.equal(s.measured, 2);
  assert.equal(s.unknown, 1);
  assert.equal(s.points.split(' ').length, 2);
  assert.equal(sparkline([rows[0]]).points, '');
});

test('diff lists only changed fields', () => {
  const d = diffRows(r({ percent: 10, text: 'a' }), r({ percent: 20, text: 'a', status: 'blocked' }));
  assert.deepEqual(d.map((x) => x.field).sort(), ['percent', 'status']);
});

test('filters combine project, status and text', () => {
  const rows = [r({ id: 1, project: 'A', text: 'deploy done' }), r({ id: 2, project: 'B', status: 'blocked', text: 'waiting' })];
  assert.equal(filterRows(rows, { project: 'A', text: '', status: '' }).length, 1);
  assert.equal(filterRows(rows, { project: '', text: 'WAIT', status: 'blocked' }).length, 1);
  assert.equal(filterRows(rows, { project: 'A', text: 'waiting', status: '' }).length, 0);
});

test('CSV neutralises formulas and quotes commas, quotes and newlines; JSON round-trips', () => {
  const rows = [r({ text: '=HYPERLINK("http://x")' }), r({ id: 2, text: 'a, "b"\nc' }), r({ id: 3, text: '-1+2' })];
  const csv = toCSV(rows);
  assert.ok(csv.includes("'=HYPERLINK"));
  assert.ok(csv.includes('"a, ""b""\nc"'));
  assert.ok(csv.includes("'-1+2"));
  assert.equal(JSON.parse(toJSON(rows)).length, 3);
});
