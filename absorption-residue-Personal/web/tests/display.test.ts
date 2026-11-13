import { test } from 'node:test';
import assert from 'node:assert/strict';
// @ts-ignore - plain-JS Pages Function module
import { onRequest, displayDTO } from '../functions/api/display/[[path]].js';

// Decision A (Oct 19): name/group/summary render UNGATED from canonical
// projects (scrubbed for credential shapes); the review gate covers only
// next/blocker/blocker_state and id exposure.
const CANARY = 'CANARY-7f3d9-opsec-do-not-leak';
const rows = [
  { id: 'p1', name: 'Tracera prod deploy', grp: 'Agent platform', status: 'active', percent: 40, detail: 'Ship the production deploy', next: CANARY, eta: CANARY, blocker: CANARY, usable: CANARY, updated_at: '2026-10-15T20:00:00.000Z', updated_by: CANARY },
  { id: 'p2', name: 'Zero progress https://github.com/KooshaPari/tracera', grp: 'Repos', status: 'held', percent: 0, detail: 'benign', next: null, eta: null, blocker: null, usable: null, updated_at: '2026-10-14T10:00:00.000Z', updated_by: 'agent' },
  { id: 'p3', name: 'Unknown progress', grp: 'Repos', status: null, percent: null, detail: null, next: null, eta: null, blocker: null, usable: null, updated_at: null, updated_by: null },
];
const subs = [
  { project_id: 'p1', name: CANARY, state: CANARY },
  { project_id: 'p1', name: 's2', state: 'done' },
];
type Opts = { withSummaries?: boolean; canaryNote?: boolean; rows?: any[]; summaries?: any[] };
const mkDb = (opts: Opts = {}) => ({
  prepare: (sql: string) => ({
    bind: () => ({ first: async () => null, all: async () => ({ results: [] }), run: async () => ({}) }),
    first: async () => null,
    run: async () => ({}),
    all: async () => {
      if (sql.includes('FROM display_summaries')) {
        if (!opts.withSummaries && !opts.summaries) throw new Error('no such table: display_summaries');
        return { results: opts.summaries ?? [{ project_id: 'p1', summary: 'CANARY-authored-summary-unused', next: 'Verify prod', blocker: null, reviewed: 1, display_name: 'CANARY-approved-name-unused', display_grp: 'CANARY-approved-grp-unused' }] };
      }
      if (sql.includes('FROM projects')) return { results: opts.rows ?? rows };
      if (sql.includes('FROM subgoals')) return { results: subs.map((s) => ({ project_id: s.project_id, c: 0 })).concat([{ project_id: 'p1', c: 2 }]) };
      if (sql.includes('FROM meta')) return { results: [{ k: 'updated', v: '2026-10-15T23:00:00.000Z' }, { k: 'note', v: opts.canaryNote ? CANARY : '' }] };
      return { results: [] };
    },
  }),
});
const req = (method = 'GET') => new Request('https://x/api/display/projects', { method });

test('display DTO renders canonical identity/summary ungated; quarantines operational prose and identifiers', async () => {
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb() }, params: { path: ['projects'] } });
  assert.equal(res.status, 200);
  const body = await res.text();
  assert.ok(!body.includes(CANARY), 'canary leaked into response body');
  assert.ok(!body.includes('updated_by'), 'updated_by key present');
  assert.ok(!body.includes('"detail"') && !body.includes('"usable"') && !body.includes('"eta"'), 'quarantined keys present');
  const d = JSON.parse(body);
  assert.equal(d.count, 3);
  assert.equal(d.projects.length, 3);
  const [a, b, c] = d.projects;
  // no display_summaries table -> gated fields closed, identity/summary still render
  assert.equal(a.id, null);
  assert.equal(a.name, 'Tracera prod deploy');
  assert.equal(a.group, 'Agent platform');
  assert.equal(a.summary, 'Ship the production deploy'); // canonical detail, ungated
  assert.equal(a.next, null); // gated field closed
  assert.equal(a.blocker, null);
  assert.equal(a.blocker_state, 'unknown');
  assert.equal(b.name, 'Zero progress https://github.com/KooshaPari/tracera'); // benign repo link renders
  assert.ok(body.includes('https://github.com/KooshaPari/tracera'), 'canonical identity must render ungated');
  assert.equal(a.needs_review, true); // gated fields unreviewed
  assert.equal(a.subgoal_count, 2);
  assert.equal(b.percent, 0); // real zero survives - not unknown
  assert.equal(c.percent, null); // unknown stays unknown, never 0
  assert.equal(a.updated_at, '2026-10-15T20:00:00.000Z'); // source mutation timestamp intact
  assert.equal(d.updated, '2026-10-15T23:00:00.000Z'); // global metadata timestamp intact
  assert.equal(d.source_updated, '2026-10-15T20:00:00.000Z'); // derived from records, not meta
  assert.ok(!('subgoals' in a) && !('detail' in a) && !('updated_by' in a));
});

test('reviewed projects unlock gated fields (id/next); unreviewed keep canonical identity', async () => {
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ withSummaries: true }) }, params: { path: ['projects'] } });
  const body = await res.text();
  assert.ok(!body.includes('CANARY-authored-summary-unused'), 'display_summaries.summary is no longer read');
  assert.ok(!body.includes('CANARY-approved-name-unused'), 'approved identity copies are retired');
  const d = JSON.parse(body);
  const [a, b] = d.projects;
  assert.equal(a.id, 'p1'); // id exposure still gated -> reviewed unlocks
  assert.equal(a.name, 'Tracera prod deploy'); // canonical, not the approved copy
  assert.equal(a.group, 'Agent platform');
  assert.equal(a.summary, 'Ship the production deploy'); // canonical detail, not authored summary
  assert.equal(a.next, 'Verify prod'); // gated field open
  assert.equal(a.needs_review, false);
  assert.equal(b.id, null); // unreviewed: id + gated fields stay closed
  assert.equal(b.name, 'Zero progress https://github.com/KooshaPari/tracera');
  assert.equal(b.group, 'Repos');
  assert.equal(b.next, null);
  assert.equal(b.needs_review, true);
});

test('parent-projects projection drops prose and updated_by', async () => {
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ canaryNote: true }) }, params: { path: ['parent-projects'] } });
  const body = await res.text();
  assert.ok(!body.includes(CANARY));
  assert.ok(!body.includes('updated_by'));
  const d = JSON.parse(body);
  assert.deepEqual(Object.keys(d.projects[0]).sort(), ['group', 'name', 'percent', 'status', 'updated_at']);
  assert.equal(d.count, 3);
});

test('empty state stays empty; errors and methods behave', async () => {
  const emptyDb = { prepare: () => ({ all: async () => ({ results: [] }), first: async () => null, run: async () => ({}) }) };
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: emptyDb }, params: { path: ['projects'] } });
  const d = JSON.parse(await res.text());
  assert.equal(d.count, 0);
  assert.deepEqual(d.projects, []);
  const noBind = await onRequest({ request: req(), env: {}, params: { path: ['projects'] } });
  assert.equal(noBind.status, 500);
  const post = await onRequest({ request: req('POST'), env: { COCKPIT_DB: emptyDb }, params: { path: ['projects'] } });
  assert.equal(post.status, 405);
  const unknown = await onRequest({ request: req(), env: { COCKPIT_DB: emptyDb }, params: { path: ['nope'] } });
  assert.equal(unknown.status, 404);
});

test('displayDTO is a pure allowlist projection (unreviewed)', () => {
  const dto = displayDTO({ id: 'x', name: 'n', grp: 'g', status: 'active', percent: 0, updated_at: '2026-10-15T20:00:00.000Z', detail: 'canon summary', next: CANARY, blocker: CANARY, usable: CANARY, eta: CANARY, updated_by: CANARY }, 4, null);
  assert.deepEqual(dto, { id: null, name: 'n', group: 'g', status: 'active', percent: 0, updated_at: '2026-10-15T20:00:00.000Z', summary: 'canon summary', next: null, blocker: null, blocker_state: 'unknown', needs_review: true, subgoal_count: 4 });
});

test('displayDTO renders canonical identity and gated fields when reviewed', () => {
  const dto = displayDTO({ id: 'x', name: 'n', grp: 'g', status: 'active', percent: 0, updated_at: null, detail: 'd' }, 4, { project_id: 'x', summary: 'CANARY-unused', next: 'ship it', blocker: null, reviewed: 1, display_name: 'CANARY-copy', display_grp: 'CANARY-copy' });
  assert.equal(dto.id, 'x');
  assert.equal(dto.name, 'n');
  assert.equal(dto.group, 'g');
  assert.equal(dto.summary, 'd');
  assert.equal(dto.next, 'ship it');
  assert.equal(dto.needs_review, false);
});

// --- field validation: adversarial input in EVERY string field --------------
test('adversarial payloads in every string field are neutralized', async () => {
  const PRIV = 'CANARY_PRIVATE_LEAK_7F3D9';
  const SK = 'xK9mQ2wP8vR4nL7jT5yU1iO3'; // credential-shaped: 24+ mixed case + digit
  const evil = [
    { id: PRIV, name: 'ok name', grp: 'g', status: PRIV, percent: 'Infinity', updated_at: PRIV, updated_by: PRIV, detail: 'rollout token=' + SK, next: PRIV },
    { id: 'evil<script>' + CANARY, name: 'X <img src=x onerror=1> payload', grp: 'G<script>payload</script>', status: 'active<script>' + CANARY, percent: 'Infinity', updated_at: CANARY + '-not-a-date', updated_by: CANARY },
    { id: 'ok2', name: '', grp: null, status: 'ACTIVE', percent: 250, updated_at: '2026-13-99T99:99:99Z' },
    { id: 'ok3', name: 'Neg pct', grp: 'g', status: 'held', percent: -5, updated_at: null },
    { id: 'ok4', name: 'session token=' + SK, grp: 'sk-' + SK, status: 'active', percent: 1, detail: SK, updated_at: null },
  ];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: evil }) }, params: { path: ['projects'] } });
  const body = await res.text();
  assert.ok(!body.includes(CANARY), 'canary leaked through identity/status/date fields');
  assert.ok(!body.includes(PRIV), 'private canary survived the gate');
  assert.ok(!body.includes(SK), 'credential-shaped value survived the ungated scrub');
  assert.ok(!body.includes('<script>') && !body.includes('<img'), 'markup survived validation');
  const d = JSON.parse(body);
  const [z, a, b, c, e] = d.projects;
  assert.deepEqual([z.id, z.name, z.group, z.status, z.percent, z.updated_at], [null, 'ok name', 'g', 'unknown', null, null]);
  assert.equal(z.summary, null); // detail carried a token= assignment -> scrubbed
  assert.equal(z.next, null); // gated field closed (unreviewed)
  assert.equal(a.id, null);
  assert.equal(a.name, 'X img src=x onerror=1 payload'); // markup stripped, canonical renders
  assert.equal(a.status, 'unknown'); // off-allowlist status dropped
  assert.equal(a.percent, null); // non-finite percent dropped
  assert.equal(a.updated_at, null); // unparseable date dropped
  assert.equal(b.name, 'Unnamed project'); // empty name falls back
  assert.equal(b.group, 'Ungrouped');
  assert.equal(b.status, 'active'); // case-normalized allowlist hit
  assert.equal(b.percent, 100); // clamped high
  assert.equal(b.updated_at, null); // invalid calendar date dropped
  assert.equal(c.percent, 0); // clamped low
  assert.equal(e.name, 'Unnamed project'); // secret-shaped name scrubbed
  assert.equal(e.group, 'Ungrouped'); // secret-shaped group scrubbed
  assert.equal(e.summary, null); // bare credential-shaped detail scrubbed
});

test('scrub passes real-world clean values: git SHAs, hyphenated slugs, the plain word token', async () => {
  const SHA = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2'; // 40-hex commit SHA, not a secret
  const r = [
    { id: 'p1', name: 'Fernet token rotation', grp: 'Security tokens', status: 'active', percent: 1, detail: 'See commit ' + SHA + ' for the rollout', updated_at: null },
    { id: 'p2', name: 'netweave-final2-test22-uncommitted-2026-07-17', grp: 'Repos', status: 'active', percent: 1, detail: null, updated_at: null },
  ];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r }) }, params: { path: ['projects'] } });
  const body = await res.text();
  const d = JSON.parse(body);
  assert.equal(d.projects[0].name, 'Fernet token rotation'); // bare keyword is not an assignment
  assert.equal(d.projects[0].group, 'Security tokens');
  assert.equal(d.projects[0].summary, 'See commit ' + SHA + ' for the rollout'); // git SHA passes
  assert.equal(d.projects[1].name, 'netweave-final2-test22-uncommitted-2026-07-17'); // slug passes
  assert.ok(body.includes(SHA));
});

test('percent strings, canonical markup, and coverage meta', async () => {
  const r = [{ id: 'p1', name: 'A', grp: 'g', status: 'active', percent: '42.5', detail: 'Safe <b>markup</b> here', updated_at: '2026-10-15T20:00:00.000Z' }];
  const sums = [
    { project_id: 'p1', summary: 'CANARY-authored-unused', next: '', blocker: null, reviewed: 1, display_name: 'CANARY', display_grp: 'CANARY' },
    { project_id: 'ghost', summary: 'x'.repeat(600), next: null, blocker: null, reviewed: 1, display_name: 'Ghost', display_grp: 'g' },
  ];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r, summaries: sums }) }, params: { path: ['projects'] } });
  const body = await res.text();
  assert.ok(!body.includes('CANARY'), 'authored display_summaries copies are no longer rendered');
  const d = JSON.parse(body);
  const p = d.projects[0];
  assert.equal(p.percent, 42.5); // numeric string accepted
  assert.equal(p.name, 'A'); // canonical identity renders
  assert.equal(p.summary, 'Safe bmarkup/b here'); // canonical detail, markup chars stripped
  assert.equal(p.next, null); // empty authored next -> null
  assert.equal(p.needs_review, false); // reviewed row present -> gated fields reviewed
  assert.equal(d.authored_count, 1); // counts gated-field review state
  assert.equal(d.needs_review_count, 0);
  assert.ok(Array.isArray(d.declared_gaps) && d.declared_gaps.includes('subgoal names and states'));
});

test('reviewed row with empty gated fields still clears needs_review; id renders', async () => {
  const r = [{ id: 'p1', name: 'A', grp: 'g', status: 'active', percent: 1, detail: null, updated_at: null }];
  const sums = [{ project_id: 'p1', summary: '   ', next: 'x', blocker: null, reviewed: 1 }];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r, summaries: sums }) }, params: { path: ['projects'] } });
  const p = JSON.parse(await res.text()).projects[0];
  assert.equal(p.summary, null); // no canonical detail
  assert.equal(p.needs_review, false); // gated fields reviewed
  assert.equal(p.next, 'x');
  assert.equal(p.id, 'p1'); // gate is the reviewed row's presence
  assert.equal(p.name, 'A'); // canonical, no approved copy needed
});

test('canonical identity renders without pattern classification (hyphens, controls, secret-shaped-but-clean)', async () => {
  const r = [
    { id: 'p-hy', name: 'User-facing next-step', grp: 'Agent platform - ops', status: 'active', percent: 10, updated_at: null },
    { id: 'p-ct', name: 'a\u0001\u001bb', grp: 'g', status: 'active', percent: 10, updated_at: null },
    { id: 'p-ss', name: 'CANARY_PRIVATE_SHAPED_7F3D9', grp: 'g', status: 'active', percent: 10, updated_at: null },
  ];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r }) }, params: { path: ['projects'] } });
  const d = JSON.parse(await res.text());
  assert.equal(d.projects[0].name, 'User-facing next-step'); // hyphen retained
  assert.equal(d.projects[0].group, 'Agent platform - ops');
  assert.equal(d.projects[1].name, 'ab'); // controls stripped (sanitization, not classification)
  assert.equal(d.projects[2].name, 'CANARY_PRIVATE_SHAPED_7F3D9'); // separator-broken runs are not credentials
});

test('unreviewed rows render canonical identity; sensitive fields stay gated', async () => {
  const r = [{ id: 'p1', name: 'A', grp: 'g', status: 'active', percent: 1, detail: 'Canon summary', updated_at: null }];
  const sums = [{ project_id: 'p1', summary: 'CANARY_PRIVATE_UNREVIEWED_9', next: 'CANARY_PRIVATE_NEXT', blocker: null, reviewed: 0 }];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r, summaries: sums }) }, params: { path: ['projects'] } });
  const body = await res.text();
  assert.ok(!body.includes('CANARY_PRIVATE'), 'unreviewed authored text leaked');
  const p = JSON.parse(body).projects[0];
  assert.equal(p.name, 'A'); // canonical renders
  assert.equal(p.group, 'g');
  assert.equal(p.summary, 'Canon summary'); // canonical detail renders
  assert.equal(p.next, null); // unreviewed authored next stays gated
  assert.equal(p.needs_review, true);
  assert.equal(p.id, null); // id exposure still gated
});

test('prototype-key project ids cannot spoof the gate on sensitive fields', async () => {
  const PRIV = 'CANARY_PRIVATE_LEAK_7F3D9';
  const r = [
    { id: 'constructor', name: 'Constructor project', grp: 'g', status: 'active', percent: 1, next: PRIV, updated_at: null },
    { id: 'toString', name: 'ToString project', grp: 'g', status: 'active', percent: 1, next: PRIV, updated_at: null },
    { id: '__proto__', name: 'Proto project', grp: 'g', status: 'active', percent: 1, next: PRIV, updated_at: null },
  ];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r }) }, params: { path: ['projects'] } });
  const body = await res.text();
  assert.ok(!body.includes(PRIV), 'inherited-property spoof opened the gate');
  const d = JSON.parse(body);
  for (const p of d.projects) {
    assert.equal(p.id, null);
    assert.equal(p.next, null);
    assert.equal(p.needs_review, true);
  }
  assert.equal(d.projects[0].name, 'Constructor project'); // canonical identity unaffected
});

test('canonical rename renders immediately; retired approved copies never override', async () => {
  const r = [{ id: 'p1', name: 'RENAMED raw canonical', grp: 'RAW GROUP', status: 'active', percent: 1, updated_at: '2026-10-15T21:00:00.000Z' }];
  const sums = [{ project_id: 'p1', summary: 's', next: null, blocker: null, reviewed: 1, display_name: 'CANARY approved name', display_grp: 'CANARY approved group' }];
  const res = await onRequest({ request: req(), env: { COCKPIT_DB: mkDb({ rows: r, summaries: sums }) }, params: { path: ['projects'] } });
  const body = await res.text();
  assert.ok(!body.includes('CANARY approved'), 'retired approved copies rendered');
  const p = JSON.parse(body).projects[0];
  assert.equal(p.name, 'RENAMED raw canonical');
  assert.equal(p.group, 'RAW GROUP');
});

test('HEAD returns headers with no body (Kilo r4289659538)', async () => {
  const res = await onRequest({ request: req('HEAD'), env: { COCKPIT_DB: mkDb() }, params: { path: ['projects'] } });
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('content-type'), 'application/json');
  assert.equal(await res.text(), '');
});
