// Economics API (D1, read-mostly). Binding: env.COCKPIT_DB. Writes need a per-agent bearer token (same tokens table as the cockpit API).
const J = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } });

async function sha256(s) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, '0')).join('');
}
async function authed(req, env) {
  const m = /^Bearer\s+(.+)$/.exec(req.headers.get('authorization') || '');
  if (!m) return false;
  const h = await sha256(m[1]);
  return !!(await env.COCKPIT_DB.prepare('SELECT actor FROM tokens WHERE sha256=? AND revoked=0').bind(h).first());
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const part = url.pathname.replace(/^\/api\/econ\/?/, '');
  const db = env.COCKPIT_DB;
  if (part === '' || part === 'summary') {
    const [plans, lanes, conns, usage, metaRows] = await Promise.all([
      db.prepare('SELECT * FROM econ_plan_terms ORDER BY effective DESC').all(),
      db.prepare('SELECT provider, access_type, COUNT(*) AS lanes FROM econ_lanes GROUP BY provider, access_type').all(),
      db.prepare('SELECT provider, auth_type, SUM(active) AS active, COUNT(*) AS total FROM econ_connections GROUP BY provider, auth_type').all(),
      db.prepare('SELECT day, SUM(requests) AS requests, SUM(spend_cents) AS spend_cents, SUM(mfu) AS mfu FROM econ_daily_usage GROUP BY day ORDER BY day DESC LIMIT 45').all(),
      db.prepare('SELECT k,v FROM meta').all(),
    ]);
    const meta = Object.fromEntries(metaRows.results.map((r) => [r.k, r.v]));
    // #70 section 2: the summary carried no metadata timestamp, so the page had
    // nothing source-derived to date its figures and fell back to render time.
    // latestDay is the newest DAY actually present in the data, which is the
    // honest freshness signal for usage: it reports what is stored, not when the
    // page happened to load. It is null when there are no rows at all.
    const latestDay = usage.results.length ? usage.results[0].day : null;
    return J({
      plans: plans.results,
      lanes: lanes.results,
      connections: conns.results,
      daily: usage.results,
      updated: meta.updated || '',
      note: meta.note || '',
      latestDay,
    });
  }
  if (part === 'usage') {
    const r = await db.prepare('SELECT day, lane_id, requests, spend_cents, mfu, coverage FROM econ_daily_usage ORDER BY day DESC LIMIT 500').all();
    return J({ rows: r.results });
  }
  return J({ error: 'unknown route' }, 404);
}

export async function onRequestPost({ request, env }) {
  if (!(await authed(request, env))) return J({ error: 'unauthorized' }, 401);
  const url = new URL(request.url);
  const part = url.pathname.replace(/^\/api\/econ\/?/, '');
  const body = await request.json();
  const db = env.COCKPIT_DB;
  if (part === 'ingest/usage') {
    // rows: [{request_id, occurred_at, lane_id, connection_id, model, status, input_tokens, cached_tokens, output_tokens, reasoning_tokens, elapsed_ms, cost_cents, provenance}]
    const rows = body.rows || [];
    let n = 0;
    for (const r of rows.slice(0, 500)) {
      await db.prepare(`INSERT INTO econ_usage_ledger (request_id, occurred_at, lane_id, connection_id, model, status, input_tokens, cached_tokens, output_tokens, reasoning_tokens, elapsed_ms, cost_cents, provenance)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(request_id) DO NOTHING`).bind(
        r.request_id, r.occurred_at, r.lane_id || null, r.connection_id || null, r.model || null, r.status ?? null,
        r.input_tokens ?? null, r.cached_tokens ?? null, r.output_tokens ?? null, r.reasoning_tokens ?? null,
        r.elapsed_ms ?? null, r.cost_cents ?? null, r.provenance || null).run();
      n++;
    }
    return J({ accepted: n });
  }
  if (part === 'ingest/connections') {
    const rows = body.rows || [];
    for (const r of rows.slice(0, 200)) {
      await db.prepare(`INSERT INTO econ_connections (id, lane_id, provider, auth_type, active, last_sync, source) VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET active=excluded.active, last_sync=excluded.last_sync, auth_type=excluded.auth_type`).bind(
        r.id, r.lane_id || null, r.provider, r.auth_type || null, r.active ? 1 : 0, r.last_sync || null, r.source || null).run();
    }
    return J({ accepted: rows.length });
  }
  if (part === 'rollup/daily') {
    await db.prepare(`INSERT INTO econ_daily_usage (day, lane_id, requests, spend_cents)
      SELECT substr(occurred_at,1,10), lane_id, COUNT(*), SUM(cost_cents) FROM econ_usage_ledger GROUP BY 1,2
      ON CONFLICT(day, lane_id) DO UPDATE SET requests=excluded.requests, spend_cents=excluded.spend_cents`).run();
    return J({ ok: true });
  }
  return J({ error: 'unknown route' }, 404);
}
