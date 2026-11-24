import { test } from 'node:test';
import assert from 'node:assert/strict';
// @ts-ignore - plain-JS Pages Function module
import { onRequest, sourceLabel, statusRowDTO } from '../functions/api/display/[[path]].js';

const CANARY = 'CANARY-7f3d9-opsec-do-not-leak';
type Tables = { dot_status?: any[]; events?: any[]; dot_digest?: any[]; digest_messages?: any[]; projects?: any[]; display_summaries?: any[] };
const calls: { sql: string; binds: any[] }[] = [];
const mkDb = (t: Tables) => ({
  prepare: (sql: string) => {
    const run = (binds: any[]) => ({
      all: async () => {
        calls.push({ sql, binds });
        const tbl = /FROM (\w+)/.exec(sql)?.[1] as keyof Tables;
        if (!(tbl in t)) throw new Error('no such table: ' + tbl);
        if (sql.includes('MAX(id)')) {
          const latest = new Map<string, any>();
          for (const r of t.dot_status ?? []) if (!latest.has(r.project_id) || latest.get(r.project_id).id < r.id) latest.set(r.project_id, r);
          return { results: [...latest.values()] };
        }
        return { results: t[tbl] };
      },
    });
    return { ...run([]), bind: (...b: any[]) => run(b) };
  },
});
const call = (db: any, qs = '') =>
  onRequest({ request: new Request('https://x/api/display/status' + qs), env: { COCKPIT_DB: db }, params: { path: ['status'] } });
const projects = [{ id: 'p1', name: 'Tracera prod deploy' }, { id: 'p2', name: 'Other' }];
const row = (o: any = {}) => ({ id: 1, project_id: 'p1', status: 'active', percent: 40, unknown_cause: null, start_step: null, text: 'Shipped', recorded_at: '2026-10-22T08:00:00.000Z', ...o });

test('label is unverified until a lane confirm row exists, then names the lane', async () => {
  assert.equal(sourceLabel(null), 'Dot-reported, unverified');
  assert.equal(sourceLabel('pipeline'), 'Dot-reported, verified by pipeline');
  const db = mkDb({ projects, dot_status: [row({ id: 1 }), row({ id: 2, text: 'Newer' })], events: [{ actor: 'pipeline', after: '{"confirm_ref":1}' }, { actor: 'x', after: 'not json' }] });
  const body = await (await call(db)).json();
  const byId = new Map(body.history.map((r: any) => [r.id, r]));
  assert.equal((byId.get(1) as any).source_label, 'Dot-reported, verified by pipeline');
  assert.equal((byId.get(1) as any).verified, true);
  assert.equal((byId.get(2) as any).source_label, 'Dot-reported, unverified');
  assert.equal(body.current.length, 1);
  assert.equal(body.current[0].id, 2);
  assert.equal(body.intake_note, null);
});

test('missing tables give an empty payload with the intake note, not an error', async () => {
  const res = await call(mkDb({}));
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.intake_note, 'no updates yet: intake not wired');
  assert.deepEqual([body.current, body.history, body.digests, body.messages], [[], [], [], []]);
  assert.equal(res.headers.get('cache-control'), 'no-store');
});

test('project id is exposed only for reviewed projects; names are scrubbed', async () => {
  const db = mkDb({ projects: [{ id: 'p1', name: 'api_key = abc123' }, { id: 'p2', name: 'Fine' }], display_summaries: [{ project_id: 'p2', reviewed: 1 }], dot_status: [row({ id: 1, project_id: 'p1' }), row({ id: 2, project_id: 'p2' })] });
  const body = await (await call(db)).json();
  const p1 = body.history.find((r: any) => r.id === 1);
  const p2 = body.history.find((r: any) => r.id === 2);
  assert.equal(p1.project_id, null);
  assert.equal(p1.project, 'Unnamed project');
  assert.equal(p2.project_id, 'p2');
});

test('null percent renders cause and start step; measured percent drops them', () => {
  const unknown = statusRowDTO(row({ percent: null, unknown_cause: 'no samples', start_step: 'size the task' }), new Map([['p1', 'P']]), new Set(), new Map());
  assert.equal(unknown.percent, null);
  assert.equal(unknown.unknown_cause, 'no samples');
  assert.equal(unknown.start_step, 'size the task');
  const known = statusRowDTO(row({ unknown_cause: 'stale' }), new Map([['p1', 'P']]), new Set(), new Map());
  assert.equal(known.percent, 40);
  assert.equal(known.unknown_cause, null);
});

test('hostile values are sanitized and secret-shaped text is dropped', async () => {
  const db = mkDb({ projects, dot_status: [row({ text: 'token: ' + CANARY, status: '<script>', percent: 900 }), row({ id: 2, text: '<b>hi</b> "x"' })] });
  const body = await (await call(db)).json();
  const a = body.history.find((r: any) => r.id === 1);
  assert.equal(a.text, null);
  assert.equal(a.status, 'unknown');
  assert.equal(a.percent, 100);
  assert.equal(JSON.stringify(body).includes(CANARY), false);
  assert.equal(body.history.find((r: any) => r.id === 2).text, 'bhi/b x');
});

test('filters are validated and bound, never interpolated', async () => {
  calls.length = 0;
  const db = mkDb({ projects, dot_status: [row()] });
  const body = await (await call(db, "?project=p1&since=2026-10-22T00:00:00Z&limit=9999")).json();
  assert.deepEqual(body.filters, { project: 'p1', since: '2026-10-22T00:00:00.000Z', limit: 200 });
  const q = calls.find((c) => c.sql.includes('FROM dot_status WHERE project_id'));
  assert.ok(q);
  assert.equal(q!.sql.includes('p1'), false);
  assert.deepEqual(q!.binds, ['p1', '2026-10-22T00:00:00.000Z', 200]);
  const bad = await (await call(db, "?project=p1';DROP TABLE x;--&since=garbage&limit=-5")).json();
  assert.deepEqual(bad.filters, { project: null, since: null, limit: 50 });
});

test('digest history and backfilled messages are read-only DTOs', async () => {
  const db = mkDb({ projects, dot_status: [row()], dot_digest: [{ id: 3, period_start: '2026-10-22T07:00:00Z', period_end: '2026-10-22T07:30:00Z', format: 'markdown', summary: 'ok', recorded_at: '2026-10-22T07:31:00Z', uri: 'secret://x' }], digest_messages: [{ digest_id: 'm1', ts: '2026-10-22T07:00:00-07:00', channel: 'imessage', author: 'main', text: 'digest text', kind: 'digest', source: 'backfill', author_original: CANARY }] });
  const body = await (await call(db)).json();
  assert.equal(body.digests[0].uri, undefined);
  assert.equal(body.messages[0].author_original, undefined);
  assert.equal(body.messages[0].source, 'backfill');
  assert.equal(JSON.stringify(body).includes(CANARY), false);
  const post = await onRequest({ request: new Request('https://x/api/display/status', { method: 'POST' }), env: { COCKPIT_DB: db }, params: { path: ['status'] } });
  assert.equal(post.status, 405);
});

test('Dot cannot self-confirm; confirm for a nonexistent row labels nothing', async () => {
  const db = mkDb({ projects, dot_status: [row({ id: 1 }), row({ id: 2 })], events: [{ actor: 'dot', after: '{"confirm_ref":1}' }, { actor: 'Dot', after: '{"confirm_ref":2}' }, { actor: 'pipeline', after: '{"confirm_ref":999}' }] });
  const body = await (await call(db)).json();
  for (const r of body.history) {
    assert.equal(r.verified, false);
    assert.equal(r.source_label, 'Dot-reported, unverified');
  }
});

test('lane_status events show as lane-reported rows and clear the intake note when dot_status is empty', async () => {
  const lane = (id: number, pid: string, headline: string) => ({ id, ts: '2026-10-22T21:49:35.329Z', actor: 'instinct-cockpit', action: 'lane_status', project_id: pid, after: JSON.stringify({ kind: 'lane_status', headline, text: 'checked 2:42 PM' }) });
  const db = mkDb({ projects, dot_status: [], events: [lane(2, 'p1', 'Newer'), lane(1, 'p1', 'Older'), { id: 3, ts: 'x', actor: 'pipeline', action: 'dot_status_confirm', project_id: null, after: '{"confirm_ref":1}' }] });
  const body = await (await call(db)).json();
  assert.equal(body.intake_note, null);
  assert.equal(body.history.length, 2);
  assert.equal(body.current.length, 1);
  assert.equal(body.current[0].source_label, 'Lane-reported (instinct-cockpit)');
  assert.equal(body.current[0].verified, false);
  assert.equal(body.current[0].project_id, null);
  assert.match(body.current[0].text, /^Newer: checked/);
});

test('intake note stays when both dot_status and lane_status are empty', async () => {
  const body = await (await call(mkDb({ projects, dot_status: [], events: [] }))).json();
  assert.equal(body.intake_note, 'no updates yet: intake not wired');
});
