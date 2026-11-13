import { test } from 'node:test';
import assert from 'node:assert/strict';
// Root functions/ is the source of truth (staged into the web build); the
// web/functions/ copies are byte-identical mirrors checked by routes.test.ts.
import { onRequest as parentReq } from '../../functions/api/parent/[[path]].js';
import { onRequest as v1Req } from '../../functions/api/v1/[[path]].js';
import { onRequest as displayReq } from '../../functions/api/display/[[path]].js';

const UPDATED = '2026-10-17T12:00:00.000Z';
const PROJECT = { id: 'p1', name: 'Alpha', grp: 'G', status: 'live', percent: 10, detail: null, next: null, eta: null, blocker: null, usable: null, position: 0, archived: 0, updated_at: UPDATED, updated_by: 'seed' };

type Row = Record<string, unknown>;
function mkDb(route: (sql: string) => Row[]) {
  const calls: string[] = [];
  const db = {
    calls,
    prepare(sql: string) {
      calls.push(sql);
      const stmt = {
        all: async () => ({ results: route(sql) }),
        first: async () => route(sql)[0] ?? null,
        run: async () => ({}),
        bind: (..._v: unknown[]) => stmt,
      };
      return stmt;
    },
  };
  return db;
}
const okRoute = (sql: string): Row[] => {
  if (/FROM meta/.test(sql)) return [{ k: 'updated', v: UPDATED }];
  if (/FROM projects/.test(sql)) return [PROJECT];
  if (/FROM subgoals/.test(sql)) return [];
  if (/display_summaries/.test(sql)) return [];
  if (/FROM tokens/.test(sql)) return [];
  if (/FROM events/.test(sql)) return [];
  return [];
};
const failRoute = (msg: string) => (_sql: string): Row[] => { throw new Error(msg); };
const req = (url: string, init: RequestInit = {}) => new Request('https://example.com' + url, init);

test('parent API: D1 failure returns JSON 503 with Retry-After, never a bare exception', async () => {
  const r = await parentReq({ request: req('/api/parent/projects'), env: { COCKPIT_DB: mkDb(failRoute('D1_ERROR: exceeded daily limit')) }, params: { path: ['projects'] } } as never);
  assert.equal(r.status, 503);
  assert.equal(r.headers.get('content-type'), 'application/json');
  const ra = Number(r.headers.get('retry-after'));
  assert.ok(ra >= 3600, `quota error should retry after midnight UTC, got ${ra}`);
  const body = await r.json() as Record<string, unknown>;
  assert.equal(body.error, 'store_unavailable');
  assert.match(String(body.detail), /daily limit/);
});

test('parent API: non-quota D1 failure gets a short Retry-After', async () => {
  const r = await parentReq({ request: req('/api/parent/projects'), env: { COCKPIT_DB: mkDb(failRoute('network reset')) }, params: { path: ['projects'] } } as never);
  assert.equal(r.status, 503);
  assert.equal(r.headers.get('retry-after'), '30');
});

test('parent API: If-None-Match short-circuits before the projects SELECT', async () => {
  const db = mkDb(okRoute);
  const first = await parentReq({ request: req('/api/parent/projects'), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(first.status, 200);
  const etag = first.headers.get('etag');
  assert.equal(etag, `"${UPDATED}"`);
  db.calls.length = 0;
  const second = await parentReq({ request: req('/api/parent/projects', { headers: { 'if-none-match': etag! } }), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(second.status, 304);
  assert.deepEqual(db.calls, ['SELECT k,v FROM meta'], '304 path must run only the cheap meta probe');
});

test('v1 API: D1 failure returns JSON 503 with Retry-After', async () => {
  const r = await v1Req({ request: req('/api/v1/projects'), env: { COCKPIT_DB: mkDb(failRoute('D1_ERROR: exceeded daily limit')) }, params: { path: ['projects'] } } as never);
  assert.equal(r.status, 503);
  assert.equal(r.headers.get('content-type'), 'application/json');
  assert.ok(Number(r.headers.get('retry-after')) >= 3600);
});

test('v1 API: write without a bearer still 401s before any D1 read', async () => {
  const db = mkDb(failRoute('must not be read'));
  const r = await v1Req({ request: req('/api/v1/projects/p1', { method: 'PATCH', body: '{}' }), env: { COCKPIT_DB: db }, params: { path: ['projects', 'p1'] } } as never);
  assert.equal(r.status, 401);
  assert.deepEqual(db.calls, [], 'unauthenticated writes must not touch D1');
});

test('v1 API: GET list honors If-None-Match with a 304', async () => {
  const db = mkDb(okRoute);
  const first = await v1Req({ request: req('/api/v1/projects'), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(first.status, 200);
  const etag = first.headers.get('etag')!;
  assert.equal(etag, `"${UPDATED}"`);
  db.calls.length = 0;
  const second = await v1Req({ request: req('/api/v1/projects', { headers: { 'if-none-match': etag } }), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(second.status, 304);
  assert.deepEqual(db.calls, ['SELECT k,v FROM meta']);
});

test('display API: D1 failure returns JSON 503 with Retry-After', async () => {
  const r = await displayReq({ request: req('/api/display/parent-projects'), env: { COCKPIT_DB: mkDb(failRoute('D1_ERROR: exceeded daily limit')) }, params: { path: ['parent-projects'] } } as never);
  assert.equal(r.status, 503);
  assert.equal(r.headers.get('content-type'), 'application/json');
  assert.ok(Number(r.headers.get('retry-after')) >= 3600);
});

test('display API: projection DTO is unchanged by the ETag reorder', async () => {
  const db = mkDb(okRoute);
  const r = await displayReq({ request: req('/api/display/projects'), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(r.status, 200);
  const body = await r.json() as Record<string, unknown>;
  assert.equal(body.count, 1);
  assert.equal(body.updated, UPDATED);
  const p = (body.projects as Row[])[0];
  assert.equal(p.name, 'Alpha', 'Decision A: canonical identity renders ungated');
  assert.equal(p.id, null);
  assert.equal(p.needs_review, true);
  assert.equal(r.headers.get('etag'), `"${UPDATED}"`);
  db.calls.length = 0;
  const second = await displayReq({ request: req('/api/display/projects', { headers: { 'if-none-match': `"${UPDATED}"` } }), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(second.status, 304);
  assert.deepEqual(db.calls, ['SELECT k,v FROM meta']);
});

test('display API: weak ETag (W/ prefix from edge compression) still yields 304', async () => {
  const db = mkDb(okRoute);
  const first = await displayReq({ request: req('/api/display/projects'), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(first.status, 200);
  const weak = await displayReq({ request: req('/api/display/projects', { headers: { 'if-none-match': 'W/"' + UPDATED + '"' } }), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(weak.status, 304, 'edge-weakened validator must short-circuit (RFC 9110 weak comparison)');
  const wrong = await displayReq({ request: req('/api/display/projects', { headers: { 'if-none-match': '"stale"' } }), env: { COCKPIT_DB: db }, params: { path: ['projects'] } } as never);
  assert.equal(wrong.status, 200, 'mismatched validator must NOT 304');
});

test('snapshot endpoint: store missing -> 503; auth and roundtrip via R2 binding', async () => {
  const db = mkDb(okRoute);
  const noStore = await parentReq({ request: req('/api/parent/snapshot'), env: { COCKPIT_DB: db }, params: { path: ['snapshot'] } } as never);
  assert.equal(noStore.status, 503);

  const store = new Map<string, string>();
  const r2 = { get: async (k: string) => (store.has(k) ? { text: async () => store.get(k)! } : null), put: async (k: string, v: string) => { store.set(k, v); } };
  const env = { COCKPIT_DB: db, COCKPIT_SNAPSHOT: r2, SNAPSHOT_TOKEN: 'secret-token' };

  const empty = await parentReq({ request: req('/api/parent/snapshot'), env, params: { path: ['snapshot'] } } as never);
  assert.equal(empty.status, 404);

  const noAuth = await parentReq({ request: req('/api/parent/snapshot', { method: 'PUT', body: '{"projects":[]}' }), env, params: { path: ['snapshot'] } } as never);
  assert.equal(noAuth.status, 401);
  const badAuth = await parentReq({ request: req('/api/parent/snapshot', { method: 'PUT', headers: { authorization: 'Bearer wrong' }, body: '{"projects":[]}' }), env, params: { path: ['snapshot'] } } as never);
  assert.equal(badAuth.status, 401);
  const badBody = await parentReq({ request: req('/api/parent/snapshot', { method: 'PUT', headers: { authorization: 'Bearer secret-token' }, body: '{"nope":1}' }), env, params: { path: ['snapshot'] } } as never);
  assert.equal(badBody.status, 400);

  const put = await parentReq({ request: req('/api/parent/snapshot', { method: 'PUT', headers: { authorization: 'Bearer secret-token' }, body: JSON.stringify({ updated: UPDATED, projects: [{ name: 'Alpha' }] }) }), env, params: { path: ['snapshot'] } } as never);
  assert.equal(put.status, 200);
  const got = await parentReq({ request: req('/api/parent/snapshot'), env, params: { path: ['snapshot'] } } as never);
  assert.equal(got.status, 200);
  assert.equal(got.headers.get('x-snapshot-source'), 'r2');
  const body = await got.json() as Record<string, unknown>;
  assert.equal((body.projects as Row[]).length, 1);
  assert.ok(typeof body.stored_at === 'string' && body.stored_at.length > 0, 'stored snapshot carries its own timestamp');
});
