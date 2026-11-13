// Cockpit state API (D1). Reads and writes need a valid per-agent bearer token (Access gates the edge; the header it injects is not trusted here).
// Every write appends a row to `events` (audit log). Binding: env.COCKPIT_DB (D1).
import { J, unavailable, sha256, actorFor } from '../http.js';

const FIELDS = ['name', 'grp', 'status', 'percent', 'detail', 'next', 'eta', 'blocker', 'usable'];
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

function rowOut(p, subs) {
  return { id: p.id, name: p.name, group: p.grp, status: p.status, percent: p.percent, detail: p.detail, next: p.next, eta: p.eta, blocker: p.blocker, usable: p.usable, subgoals: subs, updated_at: p.updated_at, updated_by: p.updated_by };
}
async function loadAll(db, metaRows) {
  const ps = (await db.prepare('SELECT * FROM projects WHERE archived=0 ORDER BY position').all()).results;
  const ss = (await db.prepare('SELECT * FROM subgoals ORDER BY project_id, position').all()).results;
  const by = {};
  for (const s of ss) (by[s.project_id] ||= []).push({ name: s.name, state: s.state });
  const meta = Object.fromEntries(metaRows.map((r) => [r.k, r.v]));
  return { note: meta.note || '', updated: meta.updated || '', projects: ps.map((p) => rowOut(p, by[p.id] || [])) };
}
async function loadOne(db, id) {
  const p = await db.prepare('SELECT * FROM projects WHERE id=?').bind(id).first();
  if (!p) return null;
  const ss = (await db.prepare('SELECT name,state FROM subgoals WHERE project_id=? ORDER BY position').bind(id).all()).results;
  return rowOut(p, ss);
}
async function audit(db, actor, action, pid, before, after, ts) {
  await db.prepare('INSERT INTO events(ts,actor,action,project_id,before,after) VALUES(?,?,?,?,?,?)')
    .bind(ts, actor, action, pid, before ? JSON.stringify(before) : null, after ? JSON.stringify(after) : null).run();
}
async function setSubgoals(db, id, subs) {
  await db.prepare('DELETE FROM subgoals WHERE project_id=?').bind(id).run();
  for (let i = 0; i < subs.length; i++)
    await db.prepare('INSERT INTO subgoals(project_id,position,name,state) VALUES(?,?,?,?)').bind(id, i, String(subs[i].name), subs[i].state ?? null).run();
}

async function handle({ request, env, params }) {
  const db = env.COCKPIT_DB;
  const path = [].concat(params.path || []);
  if (path[0] !== 'projects' && path[0] !== 'export.json' && path[0] !== 'events') return J({ error: 'not found' }, 404);
  const actor = await actorFor(request, env);
  const method = request.method;
  const write = method !== 'GET' && method !== 'HEAD';
  if (write && !actor) return J({ error: 'write requires a valid bearer token' }, 401);
  // Reads pass without a bearer: Cloudflare Access is the perimeter and exposes nothing beyond what the
  // Access-gated static pages already showed. The Access identity header stays untrusted for writes
  // (not a validated JWT), so writes still require a per-agent token for audit attribution.
  const ts = new Date().toISOString();

  if (!write && (path[0] === 'export.json' || (path[0] === 'projects' && !path[1]))) {
    // Read reduction: meta.updated keys the ETag (every write bumps it), so a
    // client holding the current version skips the full project+subgoal SELECTs.
    const metaRows = (await db.prepare('SELECT k,v FROM meta').all()).results;
    const etag = '"' + (Object.fromEntries(metaRows.map((r) => [r.k, r.v])).updated || 'empty') + '"';
    if (request.headers.get('if-none-match') === etag) return new Response(null, { status: 304, headers: { etag, 'cache-control': 'no-store' } });
    return J(await loadAll(db, metaRows), 200, { etag });
  }
  if (path[0] === 'events') {
    const rows = (await db.prepare('SELECT * FROM events ORDER BY id DESC LIMIT 200').all()).results;
    return J({ events: rows });
  }
  const id = path[1];
  if (!id) {
    if (method === 'POST') {
      const b = await request.json().catch(() => null);
      if (!b || !b.name || !b.group) return J({ error: 'name and group required' }, 400);
      const pid = b.id || slug(b.name);
      if (await db.prepare('SELECT 1 FROM projects WHERE id=?').bind(pid).first()) return J({ error: 'exists' }, 409);
      const pos = ((await db.prepare('SELECT MAX(position) m FROM projects').first()).m ?? -1) + 1;
      await db.prepare('INSERT INTO projects(id,name,grp,status,percent,detail,next,eta,blocker,usable,position,archived,updated_at,updated_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,0,?,?)')
        .bind(pid, b.name, b.group, b.status ?? null, b.percent ?? null, b.detail ?? null, b.next ?? null, b.eta ?? null, b.blocker ?? null, b.usable ?? null, pos, ts, actor).run();
      await setSubgoals(db, pid, b.subgoals || []);
      await db.prepare("INSERT INTO meta(k,v) VALUES('updated',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(ts).run();
      const after = await loadOne(db, pid);
      await audit(db, actor, 'create', pid, null, after, ts);
      return J(after, 201);
    }
    return J({ error: 'method not allowed' }, 405);
  }
  const cur = await loadOne(db, id);
  if (!cur) return J({ error: 'not found' }, 404);
  if (method === 'GET') return J(cur);
  if (method === 'PATCH') {
    const b = await request.json().catch(() => null);
    if (!b || typeof b !== 'object') return J({ error: 'json body required' }, 400);
    const sets = [], vals = [];
    for (const f of FIELDS) {
      const k = f === 'grp' ? 'group' : f;
      if (k in b) { sets.push(`${f}=?`); vals.push(b[k] ?? null); }
    }
    if (sets.length) {
      sets.push('updated_at=?', 'updated_by=?'); vals.push(ts, actor, id);
      await db.prepare(`UPDATE projects SET ${sets.join(',')} WHERE id=?`).bind(...vals).run();
    }
    if (Array.isArray(b.subgoals)) {
      await setSubgoals(db, id, b.subgoals);
      await db.prepare('UPDATE projects SET updated_at=?, updated_by=? WHERE id=?').bind(ts, actor, id).run();
    }
    await db.prepare("INSERT INTO meta(k,v) VALUES('updated',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(ts).run();
    const after = await loadOne(db, id);
    await audit(db, actor, 'update', id, cur, after, ts);
    return J(after);
  }
  if (method === 'DELETE') { // soft delete (archive), never a hard delete
    await db.prepare('UPDATE projects SET archived=1, updated_at=?, updated_by=? WHERE id=?').bind(ts, actor, id).run();
    await audit(db, actor, 'archive', id, cur, null, ts);
    // #70 section 4: archiving is a successful mutation, so the global freshness
    // stamp must move with it. Previously only the PATCH and events paths wrote
    // meta.updated, which let the header lag hours behind a real change.
    await db.prepare("INSERT INTO meta(k,v) VALUES('updated',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(ts).run();
    return J({ archived: id });
  }
  return J({ error: 'method not allowed' }, 405);
}

export async function onRequest(ctx) {
  if (!ctx.env.COCKPIT_DB) return J({ error: 'COCKPIT_DB binding missing' }, 500);
  try {
    return await handle(ctx);
  } catch (e) {
    return unavailable(e);
  }
}