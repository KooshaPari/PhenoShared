// Cockpit card answers (D1) - the owner's decisions recorded from the dashboard itself.
// Append-only ledger (Oct 19 direction: "Cockpit as immutable ledger always"): rows are
// never updated or deleted; a changed card text gets a new revision and new answers, and
// earlier answers stay as history.
//
// POST /api/answers             Record an answer. Requires a validated Cloudflare Access
//                               user JWT: signature checked against the team JWKS, iss/aud/exp
//                               pinned to this app. Requests that bypass Access (preview
//                               hostnames, direct origin) carry no valid JWT and are rejected,
//                               and service-token JWTs carry no email claim, so no agent or
//                               machine credential can mint a user answer.
// GET  /api/answers[?card_id=X] Dashboard readback; same validated user JWT. Test rows are
//                               excluded unless ?include_test=1.
// GET  /api/answers/export      Agent consumption; per-agent bearer token (tokens table,
//                               same as /api/v1). Test rows excluded unless ?include_test=1.
// Binding: env.COCKPIT_DB (D1).
import { J, unavailable, sha256, actorFor } from '../http.js';

const ACCESS_TEAM = 'https://floral-moon-c604.cloudflareaccess.com';
const ACCESS_AUD = '9249f18ab8824d0428b511a1bb86d0eca315cb88385f1063caeef6a76074a759';
let jwksCache = { at: 0, keys: [] };

const SCHEMA = `CREATE TABLE IF NOT EXISTS answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id TEXT NOT NULL,
  revision TEXT NOT NULL,
  answer_type TEXT NOT NULL,
  choice TEXT,
  facts TEXT,
  identity TEXT NOT NULL,
  created_at TEXT NOT NULL,
  test INTEGER NOT NULL DEFAULT 0
)`;
const INDEX = 'CREATE INDEX IF NOT EXISTS answers_card ON answers(card_id, id)';
async function ensureSchema(db) { await db.prepare(SCHEMA).run(); await db.prepare(INDEX).run(); }

function b64urlJson(s) {
  const b = atob(s.replace(/-/g, '+').replace(/_/g, '/'));
  return JSON.parse(b);
}
async function jwks() {
  if (jwksCache.keys.length && Date.now() - jwksCache.at < 3600000) return jwksCache.keys;
  const r = await fetch(ACCESS_TEAM + '/cdn-cgi/access/certs');
  if (!r.ok) throw new Error('jwks unavailable');
  const d = await r.json();
  jwksCache = { at: Date.now(), keys: Array.isArray(d.keys) ? d.keys : [] };
  return jwksCache.keys;
}
// Returns the authenticated human's email from a valid Access JWT, else null.
async function accessIdentity(request) {
  const jwt = request.headers.get('cf-access-jwt-assertion');
  if (!jwt) return null;
  const parts = jwt.split('.');
  if (parts.length !== 3) return null;
  let header, payload;
  try { header = b64urlJson(parts[0]); payload = b64urlJson(parts[1]); } catch { return null; }
  const aud = payload.aud;
  if (payload.iss !== ACCESS_TEAM) return null;
  if (!(aud === ACCESS_AUD || (Array.isArray(aud) && aud.includes(ACCESS_AUD)))) return null;
  if (!payload.exp || payload.exp * 1000 <= Date.now()) return null;
  const keys = await jwks();
  const jwk = keys.find((k) => k.kid === header.kid && k.kty === 'RSA');
  if (!jwk) return null;
  const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
  const data = new TextEncoder().encode(parts[0] + '.' + parts[1]);
  const sig = Uint8Array.from(atob(parts[2].replace(/-/g, '+').replace(/_/g, '/')), (c) => c.charCodeAt(0));
  if (!(await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, sig, data))) return null;
  return typeof payload.email === 'string' && payload.email ? payload.email : null;
}

const SLUG = /^(?:__test-)?[a-z0-9][a-z0-9-]{0,79}$/;
function cleanAnswer(body) {
  if (!body || typeof body !== 'object') return { error: 'JSON body required' };
  const card_id = typeof body.card_id === 'string' ? body.card_id : '';
  const revision = typeof body.revision === 'string' ? body.revision : '';
  if (!SLUG.test(card_id)) return { error: 'card_id must be a lowercase slug' };
  if (!/^[a-f0-9]{64}$/.test(revision)) return { error: 'revision must be the card content hash' };
  const type = body.type;
  if (type !== 'choice' && type !== 'facts') return { error: "type must be 'choice' or 'facts'" };
  let choice = null, facts = null;
  if (type === 'choice') {
    if (typeof body.choice !== 'string' || !body.choice || body.choice.length > 120) return { error: 'choice must be a short non-empty string' };
    choice = body.choice;
  } else {
    if (!Array.isArray(body.facts) || !body.facts.length || body.facts.length > 20) return { error: 'facts must be 1-20 entries' };
    facts = [];
    for (const f of body.facts) {
      if (!f || typeof f !== 'object' || typeof f.key !== 'string' || !/^[a-z0-9-]{1,40}$/.test(f.key)) return { error: 'each fact needs a short slug key' };
      if (typeof f.text !== 'string' || !f.text.trim() || f.text.length > 2000) return { error: 'each fact needs non-empty text (max 2000 chars)' };
      facts.push({ key: f.key, text: f.text });
    }
  }
  const test = body.test === true || card_id.startsWith('__test-') ? 1 : 0;
  return { card_id, revision, type, choice, facts: facts ? JSON.stringify(facts) : null, test };
}

function rowOut(r) {
  let facts = null;
  if (r.facts) { try { facts = JSON.parse(r.facts); } catch { facts = null; } }
  return { id: r.id, card_id: r.card_id, revision: r.revision, answer_type: r.answer_type, choice: r.choice, facts, identity: r.identity, created_at: r.created_at, test: !!r.test };
}

let statusCache = { at: 0, closed: null };
// Closed cards (explicit "decision": null in status.json) no longer accept answers. The
// dashboard hides their controls; this is the server-side backstop. Fail-closed: if the
// staged status.json cannot be read the answer is refused (503) rather than recorded -
// an unverifiable card state must not accept an unsafe write. Applies to every card_id;
// test cards are unaffected because they never appear in status.json's closed set.
async function closedCards(request, env) {
  if (statusCache.closed && Date.now() - statusCache.at < 60000) return statusCache.closed;
  try {
    const url = new URL(request.url);
    url.pathname = '/status.json'; url.search = '';
    const r = await env.ASSETS.fetch(new Request(url.toString()));
    if (!r.ok) throw new Error('status.json ' + r.status);
    const d = await r.json();
    const closed = new Set();
    for (const w of (d.writeups || [])) { if (w && typeof w.id === 'string' && 'decision' in w && w.decision === null) closed.add(w.id); }
    statusCache = { at: Date.now(), closed };
    return closed;
  } catch (e) { console.log('closedCards unavailable:', e && e.message); return null; }
}

async function handlePost(request, env, db) {
  // CSRF/cross-origin writes: JSON content-type already forces a CORS preflight this
  // function never grants (no ACAO header), and form posts cannot carry JSON. Belt on
  // top: when the browser sends fetch-metadata or Origin, it must be same-origin.
  const sfs = request.headers.get('sec-fetch-site');
  if (sfs && sfs !== 'same-origin' && sfs !== 'none') return J({ error: 'cross-site writes are not accepted' }, 403);
  const origin = request.headers.get('origin');
  if (origin && origin !== 'https://example.com') return J({ error: 'cross-origin writes are not accepted' }, 403);
  const identity = await accessIdentity(request);
  if (!identity) return J({ error: 'a verified dashboard sign-in is required to record an answer' }, 401);
  const body = await request.json().catch(() => null);
  const a = cleanAnswer(body);
  if (a.error) return J({ error: a.error }, 400);
  // Replay guard: an identical answer from the same identity within five minutes
  // returns the existing row instead of duplicating it. The ledger stays append-only.
  // The cutoff is bound as an ISO string: comparing the stored ISO timestamps against
  // datetime('now') (space separator) matches the whole UTC day, not five minutes.
  const cutoff = new Date(Date.now() - 5 * 60 * 1000).toISOString();
  const dupe = await db.prepare(
    "SELECT id, created_at FROM answers WHERE card_id=? AND revision=? AND answer_type=? AND COALESCE(choice,'')=COALESCE(?, '') AND COALESCE(facts,'')=COALESCE(?, '') AND identity=? AND created_at > ? ORDER BY id DESC LIMIT 1"
  ).bind(a.card_id, a.revision, a.type, a.choice, a.facts, identity, cutoff).first();
  if (dupe) return J({ ok: true, id: dupe.id, created_at: dupe.created_at, deduped: true });
  const closed = await closedCards(request, env);
  if (!closed) return J({ error: 'card state is temporarily unavailable; the answer was not recorded' }, 503);
  if (closed.has(a.card_id)) return J({ error: 'this card is decided and no longer accepts answers' }, 409);
  const ts = new Date().toISOString();
  const r = await db.prepare('INSERT INTO answers(card_id, revision, answer_type, choice, facts, identity, created_at, test) VALUES(?,?,?,?,?,?,?,?)')
    .bind(a.card_id, a.revision, a.type, a.choice, a.facts, identity, ts, a.test).run();
  return J({ ok: true, id: r.meta.last_row_id, created_at: ts });
}

async function handleExport(request, env, db) {
  const actor = await actorFor(request, env);
  if (!actor) return J({ error: 'export requires a valid bearer token' }, 401);
  const url = new URL(request.url);
  const includeTest = url.searchParams.get('include_test') === '1';
  const rows = (await db.prepare(`SELECT * FROM answers ${includeTest ? '' : 'WHERE test=0 '}ORDER BY id DESC LIMIT 500`).all()).results;
  return J({ answers: rows.map(rowOut) });
}

async function handleGet(request, db) {
  const identity = await accessIdentity(request);
  if (!identity) return J({ error: 'a verified dashboard sign-in is required to read answers' }, 401);
  const url = new URL(request.url);
  const card = url.searchParams.get('card_id') || '';
  const includeTest = url.searchParams.get('include_test') === '1';
  if (card) {
    const rows = (await db.prepare(`SELECT * FROM answers WHERE card_id=? ${includeTest ? '' : 'AND test=0 '}ORDER BY id`).bind(card).all()).results;
    return J({ answers: rows.map(rowOut) });
  }
  // Newest 500 selected DESC, returned ascending: the card readback treats the last
  // array element as the latest answer.
  const rows = (await db.prepare(`SELECT * FROM answers ${includeTest ? '' : 'WHERE test=0 '}ORDER BY id DESC LIMIT 500`).all()).results.reverse();
  return J({ answers: rows.map(rowOut) });
}

async function handle({ request, env, params }) {
  const db = env.COCKPIT_DB;
  const path = Array.isArray(params.path) ? params.path : [];
  if (path.length > 1 || (path[0] && path[0] !== 'export')) return J({ error: 'not found' }, 404);
  try {
    await ensureSchema(db);
    if (request.method === 'POST' && !path[0]) return await handlePost(request, env, db);
    if (request.method === 'GET' && path[0] === 'export') return await handleExport(request, env, db);
    if (request.method === 'GET' && !path[0]) return await handleGet(request, db);
    return J({ error: 'method not allowed' }, 405);
  } catch (e) { return unavailable(e); }
}

export async function onRequest(ctx) {
  if (!ctx.env.COCKPIT_DB) return J({ error: 'COCKPIT_DB binding missing' }, 500);
  try {
    return await handle(ctx);
  } catch (e) {
    return unavailable(e);
  }
}
