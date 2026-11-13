import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {boot} from './index.js';
import {SQLiteD1} from './testing/sqlite-d1.mjs';

async function fixture(t) {
  const db = new SQLiteD1();
  t.after(() => db.close());
  await boot(db);
  await db.prepare('UPDATE board SET last_ok=1,last_day=? WHERE skip=0').bind('2026-10-14').run();
  return db;
}
const recent = hours => new Date(Date.now() - hours * 3600000).toISOString();
async function add(db, day, good, bad, finished, ok = 1) {
  await db.prepare('INSERT INTO run(day,ok,boards_ok,boards_failed,finished_at) VALUES(?,?,?,?,?)')
    .bind(day, ok, good, bad, finished).run();
}
async function health(db) {
  return (await worker.fetch(new Request('https://offline.test/health'), {JOBS: db})).json();
}

test('health exposes two immutable finalized day IDs, excluding a fresh error placeholder', async t => {
  const db = await fixture(t);
  await add(db, '2026-10-10', 24, 1, recent(70), 0);
  await add(db, '2026-10-11', 25, 0, recent(50));
  await add(db, '2026-10-12', 25, 0, recent(37));
  await add(db, '2026-10-13', null, null, recent(0), 0);
  const before = await db.prepare('SELECT * FROM run ORDER BY day').all();
  const h = await health(db);
  assert.equal(h.latest_run.day, '2026-10-13');
  assert.equal(h.latest_finalized_run.day, '2026-10-12');
  assert.deepEqual(h.finalized_runs.map(r => r.day), ['2026-10-12', '2026-10-11']);
  assert.equal(h.run_identity_scheme, 'la-day-v1');
  assert.equal(h.stale_after_hours, 36);
  assert.equal(h.health, 'stale');
  assert.equal(h.age_hours, 37);
  assert.deepEqual(await db.prepare('SELECT * FROM run ORDER BY day').all(), before);
});
test('healthy recent finalization remains strict when a later attempt fails', async t => {
  const db = await fixture(t);
  await add(db, '2026-10-12', 25, 0, recent(2));
  assert.equal((await health(db)).health, 'ok');
  await add(db, '2026-10-13', null, null, recent(0), 0);
  const h = await health(db);
  assert.equal(h.health, 'degraded');
  assert.equal(h.age_hours, 2);
});
test('missing and malformed finalized counters remain visible and unhealthy', async t => {
  const db = await fixture(t);
  const missing = await health(db);
  assert.equal(missing.health, 'stale');
  assert.deepEqual(missing.finalized_runs, []);
  await add(db, '2026-10-12', 25, null, recent(2));
  const h = await health(db);
  assert.equal(h.health, 'degraded');
  assert.equal(h.finalized_runs[0].boards_failed, null);
});
test('finalized failure counts are preserved independently of live board inventory', async t => {
  const db = await fixture(t);
  await add(db, '2026-10-12', 24, 1, recent(2), 0);
  const h = await health(db);
  assert.equal(h.health, 'degraded');
  assert.equal(h.boards.last_failure, 0);
  assert.equal(h.latest_finalized_run.boards_ok, 24);
  assert.equal(h.latest_finalized_run.boards_failed, 1);
});
