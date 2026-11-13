import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {boot, finalize, isDiscoveryTitle, jfetch, recordStepError, step} from './index.js';
import {SQLiteD1} from './testing/sqlite-d1.mjs';

const DAY = '2026-10-14';
const json = (value, status = 200) => new Response(JSON.stringify(value), {status});
const leverJob = (id = 'new', title = 'Software Engineer') => ({id, text: title,
  categories: {location: 'Los Angeles, CA'}, hostedUrl: 'https://jobs.lever.co/riot/' + id,
  descriptionPlain: '$120,000 - $150,000. 2 years experience.'});

async function fixture(t, boards = [{}]) {
  const db = new SQLiteD1();
  t.after(() => db.close());
  await boot(db);
  await db.prepare('DELETE FROM board').run();
  for (const [index, board] of boards.entries()) {
    const b = {id: index + 1, ats: 'lever', slug: 'riot-' + index, company: 'Riot Games',
      tier: 1, skip: 0, last_day: null, last_ok: null, last_error: null, ...board};
    await db.prepare('INSERT INTO board(id,ats,slug,company,tier,skip,last_day,last_ok,last_error) VALUES(?,?,?,?,?,?,?,?,?)')
      .bind(b.id, b.ats, b.slug, b.company, b.tier, b.skip, b.last_day, b.last_ok, b.last_error).run();
  }
  return db;
}
async function job(db, {id = 'lever:riot-0:old', title = 'Software Engineer', first = DAY,
  seen = DAY, board = 1, yoe = 2, status = 'open'} = {}) {
  await db.prepare('INSERT INTO job(id,board_id,ext_id,title,location,loc_rank,yoe_min,first_seen,last_seen,status,detail_day) VALUES(?,?,?,?,?,?,?,?,?,?,?)')
    .bind(id, board, 'old', title, 'Los Angeles, CA', 3, yoe, first, seen, status, DAY).run();
}
async function previousRun(db) {
  await db.prepare('INSERT INTO run(day,ok,boards_ok,boards_failed) VALUES(?,1,1,0)').bind('2026-10-13').run();
}
async function health(db) {
  return (await worker.fetch(new Request('https://offline.test/health'), {JOBS: db})).json();
}
function mockedFetch(t, responses) {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async url => {
    calls.push(String(url));
    assert.ok(responses.length, 'unexpected request: ' + url);
    const value = responses.shift();
    if (value instanceof Error) throw value;
    return typeof value === 'function' ? value(url) : value;
  });
  t.mock.method(globalThis, 'setTimeout', callback => { queueMicrotask(callback); return 0; });
  return calls;
}
async function requestSequence(sequence) {
  const delays = [], calls = [];
  const fetcher = async (url, options) => {
    calls.push({url, options});
    assert.ok(sequence.length, 'too many attempts');
    const value = sequence.shift();
    if (value instanceof Error) throw value;
    return value;
  };
  let value, error;
  try { value = await jfetch('https://offline.test/jobs', {fetcher, wait: async ms => delays.push(ms)}); }
  catch (failure) { error = failure; }
  return {value, error, delays, calls};
}

test('jfetch succeeds once with JSON request headers', async () => {
  const result = await requestSequence([json({jobs: []})]);
  assert.deepEqual(result.value, {jobs: []});
  assert.equal(result.calls.length, 1);
  assert.deepEqual(result.delays, []);
  assert.equal(result.calls[0].options.headers.accept, 'application/json');
});
for (const status of [429, 500, 502, 503, 504, 599]) {
  test(`jfetch recovers HTTP ${status} with bounded backoff`, async () => {
    const result = await requestSequence([json({}, status), json({}, status), json({recovered: true})]);
    assert.deepEqual(result.value, {recovered: true});
    assert.equal(result.calls.length, 3);
    assert.deepEqual(result.delays, [250, 750]);
  });
  test(`jfetch exhausts HTTP ${status} after three attempts`, async () => {
    const result = await requestSequence(Array.from({length: 3}, () => json({}, status)));
    assert.equal(result.error.status, status);
    assert.equal(result.calls.length, 3);
    assert.deepEqual(result.delays, [250, 750]);
  });
}
for (const status of [400, 401, 403, 404, 408, 409, 422, 451]) {
  test(`jfetch fails HTTP ${status} immediately`, async () => {
    const result = await requestSequence([json({}, status)]);
    assert.equal(result.error.status, status);
    assert.equal(result.calls.length, 1);
    assert.deepEqual(result.delays, []);
  });
}
test('jfetch network failures recover or exhaust without a fourth attempt', async () => {
  const failure = new TypeError('network unavailable');
  const recovered = await requestSequence([failure, failure, json([])]);
  assert.deepEqual(recovered.value, []);
  assert.deepEqual(recovered.delays, [250, 750]);
  const failed = await requestSequence([failure, failure, failure]);
  assert.equal(failed.error, failure);
  assert.equal(failed.calls.length, 3);
});
test('jfetch retries a failed body transfer but fails invalid JSON immediately', async () => {
  const transfer = {ok: true, json: async () => {throw new TypeError('body disconnected');}};
  const recovered = await requestSequence([transfer, json({ok: true})]);
  assert.deepEqual(recovered.value, {ok: true});
  assert.deepEqual(recovered.delays, [250]);
  const invalid = await requestSequence([new Response('{invalid JSON')]);
  assert.ok(invalid.error instanceof SyntaxError);
  assert.equal(invalid.calls.length, 1);
  assert.deepEqual(invalid.delays, []);
});

test('seniority exclusions use whole words and preserve ordinary discovery titles', () => {
  for (const title of ['Staff Software Engineer', 'Software Engineer, Staff', 'Senior Staff SWE',
    'PRINCIPAL Software Engineer', 'Distinguished Engineer, Machine Learning Engineer',
    'Software Engineer – staff-level', 'Staff Software Engineer (6+ years)']) {
    assert.equal(isDiscoveryTitle(title), false, title);
  }
  for (const title of ['Software Engineer', 'Software Engineer I', 'New Grad SWE',
    'Software Developer, Stafford', 'Principalities Software Engineer']) {
    assert.equal(isDiscoveryTitle(title), true, title);
  }
  for (const title of ['Software Engineer Intern', 'Director of Software', 'Sales Manager']) {
    assert.equal(isDiscoveryTitle(title), false, title);
  }
});
test('Riot staff title cannot create a tier-1 alert, including a cached role changing level', async t => {
  const db = await fixture(t);
  await previousRun(db);
  await job(db, {id: 'lever:riot-0:cached'});
  mockedFetch(t, [json([leverJob('staff', 'Staff Software Engineer'),
    leverJob('cached', 'Principal Software Engineer'), leverJob('eligible')])]);
  assert.equal(await step({JOBS: db}, DAY), 'board riot-0 kept 1/3');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  const rows = (await db.prepare('SELECT id,status FROM job ORDER BY id').all()).results;
  assert.deepEqual(rows, [{id: 'lever:riot-0:cached', status: 'excluded_title'},
    {id: 'lever:riot-0:eligible', status: 'open'}]);
  assert.deepEqual((await db.prepare('SELECT job_id FROM alert').all()).results, [{job_id: 'lever:riot-0:eligible'}]);
});

test('a failed board gets one later retry after untouched boards, then recovers', async t => {
  const db = await fixture(t, [{}, {slug: 'healthy'}]);
  const calls = mockedFetch(t, [json({}, 404), json([]), json([leverJob()])]);
  assert.equal(await step({JOBS: db}, DAY), 'board error riot-0');
  assert.match((await db.prepare('SELECT last_error FROM board WHERE id=1').first()).last_error, /^attempt: 404 /);
  assert.equal(await step({JOBS: db}, DAY), 'board healthy kept 0/0');
  assert.equal(await step({JOBS: db}, DAY), 'board riot-0 kept 1/1');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(await step({JOBS: db}, DAY), 'idle');
  const run = await db.prepare('SELECT * FROM run WHERE day=?').bind(DAY).first();
  assert.equal(run.ok, 1);
  assert.equal(run.boards_ok, 2);
  assert.equal(run.boards_failed, 0);
  assert.equal(run.candidates, 1);
  assert.equal(calls.length, 3);
});
test('finalization excludes cached senior titles even if their board permanently failed', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 0, last_error: 'retry:v1: failed'}]);
  await previousRun(db);
  for (const [index, title] of ['Staff Software Engineer', 'PRINCIPAL SWE', 'Distinguished Software Engineer',
    'Software Engineer, Stafford', 'Principalities Software Engineer'].entries()) {
    await job(db, {id: 'cached-' + index, title, yoe: null});
  }
  await finalize(db, DAY);
  const statuses = (await db.prepare('SELECT status FROM job ORDER BY id').all()).results.map(x => x.status);
  assert.deepEqual(statuses, ['excluded_title', 'excluded_title', 'excluded_title', 'open', 'open']);
  assert.deepEqual((await db.prepare('SELECT job_id FROM alert ORDER BY job_id').all()).results,
    [{job_id: 'cached-3'}, {job_id: 'cached-4'}]);
});
test('permanent board failure is retried once, recorded and finalized degraded', async t => {
  const db = await fixture(t);
  const calls = mockedFetch(t, [json({}, 403), json({}, 403)]);
  await step({JOBS: db}, DAY);
  await step({JOBS: db}, DAY);
  assert.match((await db.prepare('SELECT last_error FROM board').first()).last_error, /^retry:v1: 403 /);
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(await step({JOBS: db}, DAY), 'idle');
  assert.equal(calls.length, 2);
  const run = await db.prepare('SELECT * FROM run WHERE day=?').bind(DAY).first();
  assert.equal(run.ok, 0);
  assert.equal(run.boards_failed, 1);
  assert.equal(run.error, '1 board(s) failed');
  assert.equal((await health(db)).health, 'degraded');
});
test('six failed transport attempts consume exactly two board passes', async t => {
  const db = await fixture(t);
  const calls = mockedFetch(t, Array.from({length: 6}, () => new TypeError('retry: network unavailable')));
  await step({JOBS: db}, DAY);
  assert.match((await db.prepare('SELECT last_error FROM board').first()).last_error, /^attempt: retry:/);
  await step({JOBS: db}, DAY);
  assert.match((await db.prepare('SELECT last_error FROM board').first()).last_error, /^retry:v1: retry:/);
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(calls.length, 6);
});
test('invalid JSON gets one board retry, and legacy NULL errors are not skipped', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 0, last_error: null}]);
  const calls = mockedFetch(t, [new Response('{broken')]);
  assert.equal(await step({JOBS: db}, DAY), 'board error riot-0');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(calls.length, 1);
});
test('legacy errors beginning with retry: are data and do not suppress a retry', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 0, last_error: 'retry: connection failed'}]);
  const calls = mockedFetch(t, [json([])]);
  assert.equal(await step({JOBS: db}, DAY), 'board riot-0 kept 0/0');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(calls.length, 1);
});
test('a retry marker from a previous day does not suppress the next day', async t => {
  const db = await fixture(t, [{last_day: '2026-10-13', last_ok: 0, last_error: 'retry: exhausted'}]);
  const calls = mockedFetch(t, [json({unexpected: 'shape'}), json([])]);
  assert.equal(await step({JOBS: db}, DAY), 'board error riot-0');
  assert.equal(await step({JOBS: db}, DAY), 'board riot-0 kept 0/0');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(calls.length, 2);
});
test('Ashby 404 fails fast then uses the existing hosted-board fallback', async t => {
  const db = await fixture(t, [{ats: 'ashby', slug: 'whatnot'}]);
  const calls = mockedFetch(t, [json({}, 404), json({data: {jobBoard: {jobPostings: []}}})]);
  assert.equal(await step({JOBS: db}, DAY), 'board whatnot kept 0/0');
  assert.equal(calls.length, 2);
  assert.match(calls[1], /non-user-graphql/);
});
test('concurrent steps claim a retry once and cannot finalize it while in flight', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 0, last_error: 'attempt: failed'}]);
  let release;
  const fetched = new Promise(resolve => {release = resolve;});
  const calls = mockedFetch(t, [() => fetched]);
  const active = step({JOBS: db}, DAY);
  // Wait for the deterministic fetch boundary, without a real timer.
  while (!calls.length) await Promise.resolve();
  assert.equal(await step({JOBS: db}, DAY), 'busy');
  assert.equal(await finalize(db, DAY), false);
  release(json([]));
  assert.equal(await active, 'board riot-0 kept 0/0');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(calls.length, 1);
});
test('a late initial failure cannot overwrite a successful retry or completed run', async t => {
  const db = await fixture(t);
  let release;
  const firstRequest = new Promise(resolve => {release = resolve;});
  const calls = mockedFetch(t, [() => firstRequest, json({}, 403), json([])]);
  const late = step({JOBS: db}, DAY);
  while (!calls.length) await Promise.resolve();
  assert.equal(await step({JOBS: db}, DAY), 'board error riot-0');
  assert.equal(await step({JOBS: db}, DAY), 'board riot-0 kept 0/0');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  release(json({}, 403));
  await late;
  const board = await db.prepare('SELECT last_ok,last_error FROM board').first();
  assert.deepEqual(board, {last_ok: 1, last_error: null});
  assert.equal((await db.prepare('SELECT ok FROM run').first()).ok, 1);
});

test('finalization does not proceed with unobserved or retryable boards', async t => {
  const db = await fixture(t, [{}, {last_day: DAY, last_ok: 0, last_error: 'attempt: failed'}]);
  await job(db);
  assert.equal(await finalize(db, DAY), false);
  assert.equal(await db.prepare('SELECT * FROM run').first(), null);
  assert.equal(await db.prepare('SELECT * FROM job_event').first(), null);
});
test('detail requests settle before finalization; permanent parse failures retain the detail_failed flag', async t => {
  const db = await fixture(t, [{ats: 'greenhouse', slug: 'riot', last_day: DAY, last_ok: 1}]);
  await job(db, {yoe: null});
  await db.prepare('UPDATE job SET detail_day=NULL,flags=?').bind('yoe_unknown').run();
  assert.equal(await finalize(db, DAY), false);
  mockedFetch(t, [new Response('{bad JSON')]);
  assert.equal(await step({JOBS: db}, DAY), 'details 1');
  assert.equal((await db.prepare('SELECT flags FROM job').first()).flags, 'yoe_unknown,detail_failed');
  assert.equal(await step({JOBS: db}, DAY), 'done');
});
test('recovered greenhouse details prevent alerts for a six-year experience requirement', async t => {
  const db = await fixture(t, [{ats: 'greenhouse', slug: 'riot', last_day: DAY, last_ok: 1}]);
  await previousRun(db);
  await job(db, {yoe: null});
  await db.prepare('UPDATE job SET detail_day=NULL').run();
  const calls = mockedFetch(t, [json({}, 503), json({content: 'Requires 6+ years of experience. $120,000 - $160,000.'})]);
  assert.equal(await step({JOBS: db}, DAY), 'details 1');
  assert.equal((await db.prepare('SELECT yoe_min FROM job').first()).yoe_min, 6);
  assert.equal(await step({JOBS: db}, DAY), 'done');
  assert.equal(await db.prepare('SELECT * FROM alert').first(), null);
  assert.equal(calls.length, 2);
});
test('closure review uses only successfully observed boards and preserves failed-board jobs', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 1}, {last_day: DAY, last_ok: 0, last_error: 'retry:v1: failed'}]);
  await job(db, {id: 'success-old', first: '2026-10-12', seen: '2026-10-12'});
  await job(db, {id: 'failed-old', board: 2, first: '2026-10-12', seen: '2026-10-12'});
  await finalize(db, DAY);
  assert.deepEqual((await db.prepare('SELECT id,status FROM job ORDER BY id').all()).results,
    [{id: 'failed-old', status: 'open'}, {id: 'success-old', status: 'needs_closure_check'}]);
});
test('zero active boards finish degraded with explicit zero counts', async t => {
  const db = await fixture(t, [{skip: 1}]);
  assert.equal(await step({JOBS: db}, DAY), 'done');
  const run = await db.prepare('SELECT * FROM run').first();
  assert.equal(run.ok, 0);
  assert.equal(run.error, 'no active boards');
  assert.equal(run.boards_ok, 0);
  assert.equal(run.boards_failed, 0);
  assert.equal((await health(db)).health, 'degraded');
});
for (const total of [1, 2, 9, 10, 25, 100]) {
  test(`one failure among ${total} boards stays degraded`, async t => {
    const boards = Array.from({length: total}, (_, i) => ({last_day: DAY, last_ok: i ? 1 : 0,
      last_error: i ? null : 'retry:v1: permanent'}));
    const db = await fixture(t, boards);
    assert.equal(await finalize(db, DAY), true);
    const run = await db.prepare('SELECT * FROM run').first();
    assert.equal(run.ok, 0);
    assert.equal(run.boards_ok, total - 1);
    assert.equal(run.boards_failed, 1);
    assert.equal((await health(db)).health, 'degraded');
  });
}
test('error-only rows recover and do not enable first-sweep alerts', async t => {
  const db = await fixture(t);
  await recordStepError(db, DAY, new Error('database temporarily unavailable'));
  mockedFetch(t, [json([leverJob()])]);
  assert.equal(await step({JOBS: db}, DAY), 'board riot-0 kept 1/1');
  assert.equal(await step({JOBS: db}, DAY), 'done');
  const run = await db.prepare('SELECT * FROM run').first();
  assert.equal(run.ok, 1);
  assert.equal(run.error, null);
  assert.equal(run.boards_ok, 1);
  assert.equal(await db.prepare('SELECT * FROM alert').first(), null);
});
test('finalization is idempotent and preserves row identity and completed counters', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 1, company: 'Disney'}]);
  await previousRun(db);
  await job(db);
  await recordStepError(db, DAY, new Error('interrupted'));
  const identity = (await db.prepare('SELECT rowid FROM run WHERE day=?').bind(DAY).first()).rowid;
  await Promise.all([finalize(db, DAY), finalize(db, DAY)]);
  const before = await db.prepare('SELECT rowid,* FROM run WHERE day=?').bind(DAY).first();
  assert.equal(before.rowid, identity);
  assert.equal(before.jobs_new, 1);
  assert.equal(before.candidates, 1);
  assert.equal((await db.prepare('SELECT count(*) n FROM job_event').first()).n, 1);
  assert.equal((await db.prepare('SELECT count(*) n FROM alert').first()).n, 2);
  await recordStepError(db, DAY, new Error('late concurrent failure'));
  assert.equal(await finalize(db, DAY), false);
  assert.deepEqual(await db.prepare('SELECT rowid,* FROM run WHERE day=?').bind(DAY).first(), before);
  assert.equal((await db.prepare('SELECT count(*) n FROM alert').first()).n, 2);
});
test('a foreign-key dependent row survives error recovery and completed-run error races', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 1}]);
  await recordStepError(db, DAY, new Error('first interruption'));
  // The SQLite adapter enables foreign keys on every connection.
  await db.prepare('CREATE TABLE run_child(day TEXT REFERENCES run(day) ON DELETE CASCADE, note TEXT)').run();
  await db.prepare('INSERT INTO run_child(day,note) VALUES(?,?)').bind(DAY, 'preserve').run();
  await finalize(db, DAY);
  await recordStepError(db, DAY, new Error('late interruption'));
  assert.deepEqual((await db.prepare('SELECT * FROM run_child').all()).results, [{day: DAY, note: 'preserve'}]);
});
test('a batch failure rolls back alerts/events/statuses and can safely resume', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 1, company: 'Disney'}]);
  await previousRun(db);
  await job(db);
  await job(db, {id: 'older', first: '2026-10-12', seen: '2026-10-12'});
  await db.prepare("CREATE TRIGGER fail_run BEFORE INSERT ON run WHEN NEW.day='2026-10-14' BEGIN SELECT RAISE(ABORT,'injected failure'); END").run();
  await assert.rejects(finalize(db, DAY), /injected failure/);
  assert.equal(await db.prepare('SELECT * FROM job_event').first(), null);
  assert.equal(await db.prepare('SELECT * FROM alert').first(), null);
  assert.equal((await db.prepare("SELECT status FROM job WHERE id='older'").first()).status, 'open');
  await db.prepare('DROP TRIGGER fail_run').run();
  assert.equal(await finalize(db, DAY), true);
  assert.equal((await db.prepare("SELECT status FROM job WHERE id='older'").first()).status, 'needs_closure_check');
  assert.equal((await db.prepare('SELECT count(*) n FROM alert').first()).n, 2);
});
test('a healthy run with failed, unchecked or empty current board inventory stays degraded', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 1}]);
  await finalize(db, DAY);
  assert.equal((await health(db)).health, 'ok');
  await db.prepare("UPDATE board SET last_ok=0,last_error='attempt: failed'").run();
  assert.equal((await health(db)).health, 'degraded');
  await db.prepare('UPDATE board SET last_day=NULL,last_ok=NULL').run();
  assert.equal((await health(db)).health, 'degraded');
  await db.prepare('DELETE FROM board').run();
  assert.equal((await health(db)).health, 'degraded');
});
test('scheduled step errors use waitUntil and resume after an error-only run', async t => {
  const db = await fixture(t, [{last_day: DAY, last_ok: 1}]);
  let pending;
  const context = {waitUntil(promise) {pending = promise;}};
  const runDay = new Date().toLocaleDateString('en-CA', {timeZone: 'America/Los_Angeles'});
  await db.prepare('UPDATE board SET last_day=?').bind(runDay).run();
  let failures = 1;
  const realBatch = db.batch.bind(db);
  t.mock.method(db, 'batch', async statements => {
    if (failures--) throw new Error('transient batch failure');
    return realBatch(statements);
  });
  await worker.scheduled({}, {JOBS: db}, context);
  assert.ok(pending instanceof Promise);
  await pending;
  let run = await db.prepare('SELECT * FROM run WHERE day=?').bind(runDay).first();
  assert.equal(run.boards_ok, null);
  assert.match(run.error, /transient batch failure/);
  await worker.scheduled({}, {JOBS: db}, context);
  await pending;
  run = await db.prepare('SELECT * FROM run WHERE day=?').bind(runDay).first();
  assert.equal(run.boards_ok, 1);
  assert.equal(run.ok, 1);
});
