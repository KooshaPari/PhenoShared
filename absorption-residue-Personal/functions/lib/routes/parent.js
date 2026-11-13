// Parent cockpit API (D1), read-only live project summaries for the /parent/ page
// plus a non-D1 snapshot store so the page never falls back to a stale build-time
// snapshot during a D1 outage. Same perimeter argument as /api/v1: Cloudflare
// Access gates the edge. Bindings: env.COCKPIT_DB (D1, live state),
// env.COCKPIT_SNAPSHOT (R2, optional fresh snapshot), env.SNAPSHOT_TOKEN (secret).
const J = (o, s = 200, h = {}) =>
  new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...h } });

async function sha256(s) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
}

// Outage hardening: a D1 failure becomes JSON 503 + Retry-After, never a bare
// worker exception page. Quota-shaped errors reset at midnight UTC (the D1 daily
// window), anything else gets a short retry.
function retryAfterSeconds(e) {
  const m = String((e && e.message) || e || '');
  if (/limit|quota|7500|D1_ERROR/i.test(m)) {
    const n = new Date();
    return Math.max(60, Math.ceil((Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate() + 1) - n.getTime()) / 1000));
  }
  return 30;
}
const unavailable = (e) =>
  J({ error: 'store_unavailable', detail: String((e && e.message) || e || 'unknown').slice(0, 300) }, 503, { 'retry-after': String(retryAfterSeconds(e)) });

async function projects(request, db) {
  // Cheap freshness probe first: meta.updated moves with every write (#70), so
  // it keys the ETag. A client holding this version skips the full SELECT -
  // this is the read-reduction path the 15-minute sweep relies on.
  const meta = Object.fromEntries((await db.prepare('SELECT k,v FROM meta').all()).results.map((r) => [r.k, r.v]));
  const etag = '"' + (meta.updated || 'empty') + '"';
  const cache = { etag, 'cache-control': 'private, no-cache' };
  if (request.headers.get('if-none-match') === etag) return new Response(null, { status: 304, headers: cache });
  const ps = (await db.prepare('SELECT name, grp, status, percent, updated_at, updated_by FROM projects WHERE archived=0 ORDER BY position').all()).results;
  // Latest mutation comes from the records themselves; meta.updated is a global
  // metadata timestamp bumped by writes/archive - NOT verification evidence.
  let sourceUpdated = '';
  for (const p of ps) if (p.updated_at && (!sourceUpdated || new Date(p.updated_at) > new Date(sourceUpdated))) sourceUpdated = p.updated_at;
  return J({
    updated: meta.updated || '',
    source_updated: sourceUpdated,
    count: ps.length,
    projects: ps.map((p) => ({ name: p.name, group: p.grp, status: p.status, percent: p.percent, updated_at: p.updated_at, updated_by: p.updated_by })),
  }, 200, cache);
}

// Non-D1 fresh fallback: the sweep PUTs its post-sweep journal here (R2 binding
// COCKPIT_SNAPSHOT), so /parent/ can render a minutes-old snapshot when D1 is
// down instead of the build-time one. PUT auth is a shared secret compared as
// digests - the D1 token table is unreadable during exactly the quota outages
// this path exists for.
async function snapshot(request, env) {
  if (request.method === 'GET') {
    if (!env.COCKPIT_SNAPSHOT) return J({ error: 'snapshot store not configured' }, 503, { 'retry-after': '300' });
    const o = await env.COCKPIT_SNAPSHOT.get('parent-projects.json');
    if (!o) return J({ error: 'no snapshot stored yet' }, 404);
    return new Response(await o.text(), { status: 200, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'x-snapshot-source': 'r2' } });
  }
  if (request.method === 'PUT') {
    if (!env.COCKPIT_SNAPSHOT || !env.SNAPSHOT_TOKEN) return J({ error: 'snapshot store not configured' }, 503, { 'retry-after': '300' });
    const m = /^Bearer\s+(.+)$/.exec(request.headers.get('authorization') || '');
    const ok = m && (await sha256(m[1])) === (await sha256(env.SNAPSHOT_TOKEN));
    if (!ok) return J({ error: 'snapshot write requires the snapshot token' }, 401);
    const raw = await request.text();
    if (raw.length > 1000000) return J({ error: 'snapshot too large' }, 413);
    let body;
    try { body = JSON.parse(raw); } catch { return J({ error: 'json body required' }, 400); }
    if (!body || typeof body !== 'object' || !Array.isArray(body.projects)) return J({ error: 'snapshot must be an object with a projects array' }, 400);
    const stored = JSON.stringify({ ...body, stored_at: new Date().toISOString() });
    await env.COCKPIT_SNAPSHOT.put('parent-projects.json', stored);
    return J({ stored: true, bytes: stored.length });
  }
  return J({ error: 'method not allowed' }, 405);
}

export async function onRequest({ request, env, params }) {
  if (!env.COCKPIT_DB) return J({ error: 'COCKPIT_DB binding missing' }, 500);
  const path = [].concat(params.path || []);
  try {
    if (path[0] === 'snapshot') return await snapshot(request, env);
    if (path[0] !== 'projects') return J({ error: 'not found' }, 404);
    if (request.method !== 'GET' && request.method !== 'HEAD') return J({ error: 'method not allowed' }, 405);
    return await projects(request, env.COCKPIT_DB);
  } catch (e) {
    return unavailable(e);
  }
}
