import { test } from 'node:test';
import assert from 'node:assert/strict';
// @ts-ignore - TS module under node --experimental-strip-types
import { decision, revision } from '../src/features/jobs/model.ts';

test('decision: missing field stays undefined (active card, default controls)', () => {
  assert.equal(decision(undefined), undefined);
});
test('decision: explicit null means closed (no controls)', () => {
  assert.equal(decision(null), null);
});
test('decision: valid choice config passes through', () => {
  const d = decision({ type: 'choice', options: [{ key: 'approve', label: 'Approve' }] });
  assert.equal(d && d.type, 'choice');
});
test('decision: invalid or non-object config is closed, not defaulted', () => {
  assert.equal(decision({ type: 'nope' }), null);
  assert.equal(decision(42), null);
});
test('revision: null and missing decision hash identically (ledger stability)', async () => {
  const base = { company: 'A', role: 'B', text: 'C', id: 'x' };
  const r1 = await revision({ ...base, decision: null });
  const r2 = await revision(base);
  assert.equal(r1, r2);
});

// Backend boundary: the answers Pages Function enforces closed-card rejection itself,
// fails closed when card state cannot be read, and has no caller-choosable bypass.
import { onRequest as answersReq } from '../../functions/api/answers/[[path]].js';

const b64 = (o: unknown) => Buffer.from(JSON.stringify(o)).toString('base64url');
async function ownerJwt() {
  const pair = await crypto.subtle.generateKey(
    { name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' },
    true, ['sign', 'verify']);
  const jwk = await crypto.subtle.exportKey('jwk', pair.publicKey) as JsonWebKey & { kid?: string };
  jwk.kid = 'k1';
  globalThis.fetch = (async () => ({ ok: true, json: async () => ({ keys: [jwk] }) })) as unknown as typeof fetch;
  const header = b64({ alg: 'RS256', kid: 'k1', typ: 'JWT' });
  const payload = b64({
    iss: 'https://floral-moon-c604.cloudflareaccess.com',
    aud: '9249f18ab8824d0428b511a1bb86d0eca315cb88385f1063caeef6a76074a759',
    exp: Math.floor(Date.now() / 1000) + 600,
    email: 'owner@example.com',
  });
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', pair.privateKey, new TextEncoder().encode(header + '.' + payload));
  return header + '.' + payload + '.' + Buffer.from(sig).toString('base64url');
}
function mkAnswersDb() {
  const state = { inserts: 0 };
  const db = {
    prepare(sql: string) {
      const stmt = {
        bind: (..._v: unknown[]) => stmt,
        first: async () => null,
        all: async () => ({ results: [] }),
        run: async () => { if (sql.startsWith('INSERT INTO answers')) state.inserts++; return { meta: { last_row_id: 1 } }; },
      };
      return stmt;
    },
  };
  return { db, state };
}
const STATUS = { writeups: [
  { id: 'closed-card', company: 'A', role: 'B', text: 'T', decision: null },
  { id: 'open-card', company: 'C', role: 'D', text: 'U', decision: { type: 'choice', options: [{ key: 'pursue', label: 'Pursue' }] } },
] };
type AnswersDb = ReturnType<typeof mkAnswersDb>['db'];
function answersEnv(db: AnswersDb, assetsOk: boolean) {
  return {
    COCKPIT_DB: db,
    ASSETS: { fetch: async () => assetsOk
      ? ({ ok: true, json: async () => STATUS })
      : ({ ok: false, status: 500, json: async () => ({}) }) },
  };
}
async function postAnswer(jwt: string, env: ReturnType<typeof answersEnv>, cardId: string) {
  const request = new Request('https://example.com/api/answers', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'cf-access-jwt-assertion': jwt, 'sec-fetch-site': 'same-origin' },
    body: JSON.stringify({ card_id: cardId, revision: 'a'.repeat(64), type: 'choice', choice: 'pursue' }),
  });
  const res = await answersReq({ request, env, params: { path: [] } });
  return { status: res.status, body: await res.json() };
}

// One shared identity: the function caches JWKS for an hour, so every test signs with
// the same keypair. Order matters for the 60s closedCards cache: the fail-closed cases
// run before any successful status.json read populates the cache.
let JWT = null;
async function jwt() { return JWT ||= await ownerJwt(); }

test('backend: unreadable card state fails closed (503) and records nothing', async () => {
  const { db, state } = mkAnswersDb();
  const r = await postAnswer(await jwt(), answersEnv(db, false), 'open-card');
  assert.equal(r.status, 503);
  assert.equal(state.inserts, 0);
});
test('backend: no __test- prefix bypass when card state is unreadable', async () => {
  const { db, state } = mkAnswersDb();
  const r = await postAnswer(await jwt(), answersEnv(db, false), '__test-probe');
  assert.equal(r.status, 503);
  assert.equal(state.inserts, 0);
});
test('backend: POST to a closed card is rejected 409 and records nothing', async () => {
  const { db, state } = mkAnswersDb();
  const r = await postAnswer(await jwt(), answersEnv(db, true), 'closed-card');
  assert.equal(r.status, 409);
  assert.equal(state.inserts, 0);
});
test('backend: open card still records an answer (insert issued)', async () => {
  const { db, state } = mkAnswersDb();
  const r = await postAnswer(await jwt(), answersEnv(db, true), 'open-card');
  assert.equal(r.status, 200);
  assert.equal(state.inserts, 1);
});
