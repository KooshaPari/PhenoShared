import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalize, receiptUrl, localDay, counts, updatedLabel, decision, revision } from '../src/features/jobs/model.ts';
test('missing scalar fields retain records and blocked / unfamiliar statuses stay visible', () => {
  const data = normalize({ applications: [{}, { status: 'blocked' }, { status: 'new-state', company: { bad: true } }] });
  assert.deepEqual(data.applications.map(a => a.status), ['unknown', 'blocked', 'unknown']);
  assert.equal(data.applications[2].rawStatus, 'new-state'); assert.equal(data.applications[2].company, ''); assert.deepEqual(data.writeups, []); assert.deepEqual(normalize({ applications: [], writeups: null }).writeups, []); assert.equal(data.dailyTarget, '—');
});
test('invalid collections produce errors instead of silently returning zero counts', () => {
  for (const value of [null, {}, { applications: null }, { applications: {} }, { applications: [null] }, { applications: [], writeups: {} }]) assert.throws(() => normalize(value));
});
test('receipt permits only safe HTTPS direct or legacy markdown URLs', () => {
  assert.equal(receiptUrl('[receipt](https://example.com/confirmation)'), 'https://example.com/confirmation'); assert.equal(receiptUrl('https://example.com/a?q=1'), 'https://example.com/a?q=1');
  for (const value of ['javascript:alert(1)', 'http://example.com', '//example.com', 'https://user:pass@example.com', {}, null]) assert.equal(receiptUrl(value), null);
});
test('decision configs validate shape and drop malformed entries', () => {
  assert.equal(decision(null), null); assert.equal(decision(undefined), undefined); assert.equal(decision('choice'), null);
  assert.deepEqual(decision({ type: 'choice', options: [{ key: 'pursue', label: 'Pursue' }, { key: '', label: 'x' }, { key: 'decline', label: 'Decline' }] }), { type: 'choice', options: [{ key: 'pursue', label: 'Pursue' }, { key: 'decline', label: 'Decline' }] });
  assert.deepEqual(decision({ type: 'facts', questions: [{ key: 'graduation-day', label: 'Exact graduation day?' }] }), { type: 'facts', questions: [{ key: 'graduation-day', label: 'Exact graduation day?' }] });
  assert.equal(decision({ type: 'choice', options: [] }), null); assert.equal(decision({ type: 'other' }), null);
});
test('writeups carry stable ids and decision configs through normalize', () => {
  const data = normalize({ applications: [], writeups: [{ company: 'A & B', role: 'Engineer', text: 'Draft', id: 'a-b', decision: { type: 'choice', options: [{ key: 'approve', label: 'Approve' }] } }, { company: 'C', text: 'No id' }] });
  assert.equal(data.writeups[0].id, 'a-b');
  assert.deepEqual(data.writeups[0].decision, { type: 'choice', options: [{ key: 'approve', label: 'Approve' }] });
  assert.equal(data.writeups[1].id, ''); assert.equal(data.writeups[1].decision, undefined);
});
test('revision binds to exact card content and changes with any field', async () => {
  const w = { company: 'A & B', role: 'Engineer', text: 'Draft', id: 'a-b', decision: { type: 'choice' as const, options: [{ key: 'approve', label: 'Approve' }] } };
  const r0 = await revision(w);
  assert.match(r0, /^[a-f0-9]{64}$/);
  assert.equal(await revision(w), r0);
  assert.notEqual(await revision({ ...w, text: 'Draft v2' }), r0);
  assert.notEqual(await revision({ ...w, decision: null }), r0);
  assert.equal(await revision({ ...w, id: 'other-id' }), r0, 'id is not part of the revision basis');
});
test('today uses exact local calendar dates rather than timestamp prefixes', () => {
  const date = new Date(2026, 9, 9, 23, 58), day = localDay(date); assert.equal(day, '2026-10-09');
  const d = normalize({ applications: [{ status: 'sent', date: day }, { status: 'sent', date: day + 'T12:00:00Z' }, { status: 'sent', date: '2026-10-08' }, { status: 'tap', date: day }] });
  assert.deepEqual(counts(d, day), { rejected: 0,
    sent: 3, today: 1, tap: 1 });
  assert.equal(updatedLabel(''), 'Updated time unavailable'); assert.equal(updatedLabel('2026-10-09T12:00:00Z', Date.parse('2026-10-09T12:02:00Z')), 'Updated 2 minutes ago');
});
