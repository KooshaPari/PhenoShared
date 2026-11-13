// Safe display projection (read-only). Browser-facing DTOs for the Projects and
// Parent pages. /api/v1 stays canonical for machine clients; this endpoint emits
// an allowlisted presentation DTO. Decision A (Oct 19): identity and summary
// render UNGATED from canonical projects (name/grp/detail) behind a defensive
// secret scrub - a credential-shaped value quarantines to that field's fallback.
// The review gate now covers only sensitive operational fields sourced from
// REVIEWED display_summaries rows: next, blocker, blocker_state and project id
// exposure. Rendered values are still sanitized (control chars and markup
// characters stripped, length-capped), status is allowlisted, percent is
// finite+clamped, timestamps must parse. needs_review flags the GATED fields
// only (no reviewed row). D1 source records are never touched.
// Binding: env.COCKPIT_DB.
const HDRS = { 'content-type': 'application/json', 'cache-control': 'no-store' };
const J = (o, s = 200, head = false, h = {}) => new Response(head ? null : JSON.stringify(o), { status: s, headers: { ...HDRS, ...h } });

// Outage hardening: a D1 failure becomes JSON 503 + Retry-After, never a bare
// worker exception page. Quota-shaped errors reset at midnight UTC (the D1
// daily window), anything else gets a short retry.
function retryAfterSeconds(e) {
  const m = String((e && e.message) || e || '');
  if (/limit|quota|7500|D1_ERROR/i.test(m)) {
    const n = new Date();
    return Math.max(60, Math.ceil((Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate() + 1) - n.getTime()) / 1000));
  }
  return 30;
}
const unavailable = (e, head) =>
  J({ error: 'store_unavailable', detail: String((e && e.message) || e || 'unknown').slice(0, 300) }, 503, head, { 'retry-after': String(retryAfterSeconds(e)) });

// --- per-field validators + sanitization (no content classification) --------
// Strip C0/C1 control characters only; printable text (hyphens included) stays.
const stripCtl = (s) => s.replace(/[\u0000-\u001F\u007F-\u009F]/g, '');
// Sanitize a value for display: control chars and markup characters stripped,
// trimmed, length-capped. This is hygiene, not a safety boundary - the
// provenance gate (reviewed=1) is the boundary.
const clean = (v, max) => {
  if (typeof v !== 'string') return null;
  const t = stripCtl(v).replace(/[<>&"']/g, '').trim();
  return t.slice(0, max).trim() || null;
};
const STATUSES = new Set(['active', 'held', 'paused', 'blocked', 'partly-blocked', 'planning', 'in-progress', 'todo', 'done', 'archived', 'live', 'in-review', 'unknown']);
// Reviewed enum mapping for the raw values in the canonical projects ledger
// (web/src/data/projects.json): normalize case, then alias real-world variants
// to a canonical status instead of degrading them to 'unknown'.
const STATUS_ALIASES = new Map([
  ['in progress', 'in-progress'], ['working', 'in-progress'],
  ['partly blocked', 'partly-blocked'], ['partial', 'partly-blocked'],
  ['running', 'live'],
  ['in review', 'in-review'], ['awaiting review', 'in-review'],
  ['not started', 'todo'], ['saved', 'todo'],
  ['design only', 'planning'],
  ['not assessed', 'unknown'],
  ['waiting on him', 'held'],
]);
const safeStatus = (v) => {
  if (typeof v !== 'string') return 'unknown';
  const t = v.trim().toLowerCase();
  if (STATUSES.has(t)) return t;
  if (STATUS_ALIASES.has(t)) return STATUS_ALIASES.get(t);
  // Prefixed operational detail ("blocked on Mac") keeps its class; the
  // qualifier is not display-safe and intentionally dropped.
  if (t.startsWith('blocked')) return 'blocked';
  return 'unknown';
};
const safePercent = (v) => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN;
  if (!Number.isFinite(n)) return null;
  return Math.min(100, Math.max(0, Math.round(n * 100) / 100));
};
const safeDate = (v) => {
  if (typeof v !== 'string' || !v) return null;
  const t = new Date(v);
  return Number.isNaN(t.getTime()) ? null : t.toISOString();
};
const safeCount = (v) => (Number.isInteger(v) && v >= 0 ? v : 0);

// Decision A defensive scrub for ungated canonical fields. The provenance gate
// no longer covers name/group/summary, so a credential-shaped value quarantines
// to that field's fallback. Assignment-shaped keywords only - the plain word
// "token" in a project name stays displayable (Oct 19 data scan: clean).
// Separator-free base64/base62 runs with mixed case + digit, 24+ chars, read as
// credentials; hyphenated slugs break the run and 40-hex git SHAs pass.
const SECRET_ASSIGN = /\b(?:api[-_ ]?key|token|secret|password|passwd|bearer|private[-_ ]?key)\b\s*(?:[:=]|is)\s*\S/i;
const ENTROPY_RUN = /[A-Za-z0-9+/=]{24,}/g;
const looksSecret = (v) => {
  if (typeof v !== 'string') return false;
  if (SECRET_ASSIGN.test(v)) return true;
  const runs = v.match(ENTROPY_RUN);
  if (!runs) return false;
  return runs.some((t) => !/^[0-9a-f]{40}$/i.test(t) && /[a-z]/.test(t) && /[A-Z]/.test(t) && /\d/.test(t));
};
const scrubUngated = (v) => (looksSecret(v) ? null : v);

// Declared gaps: field classes this projection intentionally never emits -
// declared with descriptive labels (never the quarantined key names).
const DECLARED_GAPS = ['subgoal names and states', 'eta and usability', 'author identity', 'internal notes', 'unreviewed next/blocker detail'];

export function displayDTO(p, subgoalCount, authored) {
  // authored = a REVIEWED display_summaries row, or null. Decision A (Oct 19):
  // name/group/summary render UNGATED from canonical p.name/p.grp/p.detail
  // through the secret scrub; the review gate now covers only the sensitive
  // operational fields next/blocker/blocker_state and project id exposure.
  const a = authored || null;
  const gated = a !== null;
  return {
    id: gated ? clean(p.id, 64) : null,
    name: scrubUngated(clean(p.name, 120)) || 'Unnamed project',
    group: scrubUngated(clean(p.grp, 80)) || 'Ungrouped',
    status: safeStatus(p.status),
    percent: safePercent(p.percent),
    updated_at: safeDate(p.updated_at),
    summary: scrubUngated(clean(p.detail, 500)),
    next: a ? clean(a.next, 500) : null,
    blocker: a ? clean(a.blocker, 500) : null,
    // Explicit tri-state: 'none' = a reviewed row records no blocker (known
    // none); 'known' = reviewed blocker text; 'unknown' = no reviewed row, so
    // absence cannot be told apart from missing review.
    // Explicit reviewed blocker state wins; without it a blank blocker is
    // 'unknown', never an assumed 'none'.
    blocker_state: (() => {
      if (a === null) return 'unknown';
      const bs = typeof a.blocker_state === 'string' ? a.blocker_state.trim().toLowerCase() : '';
      if (bs === 'none' || bs === 'known' || bs === 'unknown') return bs;
      return clean(a.blocker, 500) ? 'known' : 'unknown';
    })(),
    // Review state of the GATED fields only: identity and summary no longer
    // need review. needs_review=true means no reviewed row backs next/blocker/id.
    needs_review: !gated,
    subgoal_count: safeCount(subgoalCount),
  };
}

async function loadDisplay(db, metaRows) {
  const ps = (await db.prepare('SELECT id, name, grp, status, percent, detail, updated_at FROM projects WHERE archived=0 ORDER BY position').all()).results;
  // Prototype-safe containers: project ids are attacker-influenceable strings
  // ("constructor", "toString", "__proto__"); plain-object lookups would read
  // inherited properties and spoof the gate. Maps + own checks only.
  const counts = new Map();
  for (const r of (await db.prepare('SELECT project_id, COUNT(*) c FROM subgoals GROUP BY project_id').all()).results) counts.set(r.project_id, r.c);
  const authored = new Map();
  try {
    // Provenance gate (sensitive fields only, Decision A): rows explicitly
    // marked reviewed unlock next/blocker/blocker_state and id exposure. If
    // the reviewed column or the table itself is absent, those fields
    // quarantine behind the fallbacks while identity/summary still render
    // from canonical projects.
    // SELECT * so an older table without blocker_state still works;
    // the explicit reviewed blocker-state column is read defensively below.
    const rows = (await db.prepare('SELECT * FROM display_summaries').all()).results;
    for (const r of rows) if (r.reviewed === 1) authored.set(r.project_id, r);
  } catch { /* display_summaries is optional; without it every card needs review */ }
  const meta = Object.fromEntries(metaRows.map((r) => [r.k, r.v]));
  // Latest mutation comes from the records themselves; meta.updated is a global
  // metadata timestamp bumped by writes/archive - NOT verification evidence.
  let sourceUpdated = '';
  for (const p of ps) if (p.updated_at && (!sourceUpdated || new Date(p.updated_at) > new Date(sourceUpdated))) sourceUpdated = p.updated_at;
  const projects = ps.map((p) => displayDTO(p, counts.get(p.id) || 0, authored.get(p.id)));
  return {
    updated: safeDate(meta.updated),
    source_updated: safeDate(sourceUpdated),
    count: projects.length,
    authored_count: projects.filter((x) => !x.needs_review).length,
    needs_review_count: projects.filter((x) => x.needs_review).length,
    declared_gaps: DECLARED_GAPS,
    projects,
  };
}


// --- Status tab DTO (spec 17.2 + 18) ----------------------------------------
// GET /api/display/status?project=&since=&limit=  (read-only, no-store).
// Sources: dot_status (current + history), events (confirm rows), dot_digest and
// digest_messages (history). Every source table is optional: a missing table
// yields empty data plus an explicit intake note, never an exception page.
// Confirmation contract: a lane confirms a dot_status row by appending an
// events row with action='dot_status_confirm', actor=<lane> and after=JSON
// {"confirm_ref": <dot_status.id>}. Until then the label is
// "Dot-reported, unverified". The label never changes reviewed and never feeds
// the gated next/blocker/id fields.
const LABEL_UNVERIFIED = 'Dot-reported, unverified';
const STATUS_INTAKE_NOTE = 'no updates yet: intake not wired';
const MAX_STATUS_LIMIT = 200;
const DEFAULT_STATUS_LIMIT = 50;
const safeLimit = (v) => {
  const n = Number.parseInt(v, 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_STATUS_LIMIT;
  return Math.min(n, MAX_STATUS_LIMIT);
};
const safeSlug = (v) => {
  if (typeof v !== 'string') return null;
  const t = v.trim();
  return /^[A-Za-z0-9._-]{1,64}$/.test(t) ? t : null;
};
const confirmRef = (after) => {
  try {
    const o = JSON.parse(after);
    const n = o && Number.isInteger(o.confirm_ref) ? o.confirm_ref : null;
    return n;
  } catch { return null; }
};
export const sourceLabel = (confirmer) => {
  const lane = confirmer ? clean(confirmer, 40) : null;
  return lane ? 'Dot-reported, verified by ' + lane : LABEL_UNVERIFIED;
};
export function statusRowDTO(r, names, reviewed, confirmers) {
  const pid = typeof r.project_id === 'string' ? r.project_id : '';
  const pct = safePercent(r.percent);
  return {
    id: Number.isInteger(r.id) ? r.id : null,
    project: scrubUngated(clean(names.get(pid) || '', 120)) || 'Unnamed project',
    project_id: reviewed.has(pid) ? clean(pid, 64) : null,
    status: safeStatus(r.status),
    percent: pct,
    // A null percent is shown as "?" with its cause and start step (spec 17.3).
    unknown_cause: pct === null ? scrubUngated(clean(r.unknown_cause, 200)) : null,
    start_step: pct === null ? scrubUngated(clean(r.start_step, 200)) : null,
    text: scrubUngated(clean(r.text, 500)),
    recorded_at: safeDate(r.recorded_at),
    source_label: sourceLabel(confirmers.get(r.id) || null),
    verified: confirmers.has(r.id),
  };
}
// events row (action='lane_status') -> a status row labeled by the reporting lane. The lane's
// headline and text are scrubbed like every other free-text field; project_id is never exposed.
export function laneRowDTO(r, names) {
  let o = {};
  try { o = JSON.parse(r.after) || {}; } catch { o = {}; }
  const pid = typeof r.project_id === 'string' ? r.project_id : '';
  const headline = scrubUngated(clean(o.headline, 120));
  const text = scrubUngated(clean(o.text, 500));
  const lane = clean(r.actor, 40) || 'lane';
  return {
    id: null,
    event_id: Number.isInteger(r.id) ? r.id : null,
    project: scrubUngated(clean(names.get(pid) || '', 120)) || headline || 'Lane update',
    project_id: null,
    status: safeStatus(o.status),
    percent: null,
    unknown_cause: null,
    start_step: null,
    text: headline && text ? headline + ': ' + text : text || headline,
    recorded_at: safeDate(r.ts),
    source_label: 'Lane-reported (' + lane + ')',
    verified: false,
    _pid: pid,
  };
}
async function optionalAll(db, sql, binds = []) {
  try {
    return (await db.prepare(sql).bind(...binds).all()).results || [];
  } catch { return null; }
}
async function loadStatus(db, url) {
  const project = safeSlug(url.searchParams.get('project'));
  const since = safeDate(url.searchParams.get('since'));
  const limit = safeLimit(url.searchParams.get('limit'));
  const projects = (await optionalAll(db, 'SELECT id, name FROM projects WHERE archived=0')) || [];
  const names = new Map(projects.map((p) => [p.id, p.name]));
  const reviewed = new Set();
  for (const r of (await optionalAll(db, 'SELECT * FROM display_summaries')) || []) if (r.reviewed === 1) reviewed.add(r.project_id);
  const conds = [];
  const binds = [];
  if (project) { conds.push('project_id = ?'); binds.push(project); }
  if (since) { conds.push('recorded_at >= ?'); binds.push(since); }
  const where = conds.length ? ' WHERE ' + conds.join(' AND ') : '';
  const cols = 'id, project_id, status, percent, unknown_cause, start_step, text, recorded_at';
  const histRows = await optionalAll(db, 'SELECT ' + cols + ' FROM dot_status' + where + ' ORDER BY id DESC LIMIT ?', [...binds, limit]);
  const curRows = await optionalAll(db, 'SELECT ' + cols + ' FROM dot_status WHERE id IN (SELECT MAX(id) FROM dot_status' + (project ? ' WHERE project_id = ?' : '') + ' GROUP BY project_id)', project ? [project] : []);
  const confirmers = new Map();
  for (const e of (await optionalAll(db, "SELECT actor, after FROM events WHERE action = 'dot_status_confirm' ORDER BY id")) || []) {
    const ref = confirmRef(e.after);
    // Only a lane can confirm: Dot cannot confirm its own rows. The ref must name a
    // dot_status row that is actually returned (statusRowDTO looks it up by id).
    if (ref !== null && typeof e.actor === 'string' && e.actor && e.actor.trim().toLowerCase() !== 'dot') confirmers.set(ref, e.actor);
  }
  const mapRows = (rows) => (rows || []).map((r) => statusRowDTO(r, names, reviewed, confirmers));
  const digestRows = await optionalAll(db, 'SELECT id, period_start, period_end, format, summary, recorded_at FROM dot_digest ORDER BY id DESC LIMIT ?', [limit]);
  const msgRows = await optionalAll(db, 'SELECT digest_id, ts, channel, author, text, kind, source FROM digest_messages' + (since ? ' WHERE ts >= ?' : '') + ' ORDER BY ts DESC LIMIT ?', since ? [since, limit] : [limit]);
  const dotCurrent = mapRows(curRows);
  const dotHistory = mapRows(histRows);
  // Lane-reported updates (events action='lane_status') are a second source. They are labeled by the
  // reporting lane and are never marked verified; each lane row carries event_id, not a dot_status id.
  const laneConds = ["action = 'lane_status'"];
  const laneBinds = [];
  if (project) { laneConds.push('project_id = ?'); laneBinds.push(project); }
  if (since) { laneConds.push('ts >= ?'); laneBinds.push(since); }
  const laneRaw = await optionalAll(db, 'SELECT id, ts, actor, action, project_id, after FROM events WHERE ' + laneConds.join(' AND ') + ' ORDER BY id DESC LIMIT ?', [...laneBinds, limit]);
  const laneHistory = (laneRaw || []).filter((r) => r.action === 'lane_status').map((r) => laneRowDTO(r, names));
  const laneSeen = new Set();
  const laneCurrent = laneHistory.filter((r) => { const k = r._pid; if (laneSeen.has(k)) return false; laneSeen.add(k); return true; });
  const stripPid = (r) => { const { _pid, ...rest } = r; return rest; };
  const byRecent = (a, b) => (b.recorded_at || '').localeCompare(a.recorded_at || '');
  const current = [...dotCurrent, ...laneCurrent.map(stripPid)];
  const history = [...dotHistory, ...laneHistory.map(stripPid)].sort(byRecent).slice(0, limit);
  const wired = (histRows !== null && dotHistory.length + dotCurrent.length > 0) || laneHistory.length > 0;
  return {
    intake_note: wired ? null : STATUS_INTAKE_NOTE,
    filters: { project, since, limit },
    current,
    history,
    digests: (digestRows || []).map((d) => ({
      id: Number.isInteger(d.id) ? d.id : null,
      period_start: safeDate(d.period_start),
      period_end: safeDate(d.period_end),
      format: clean(d.format, 16),
      summary: scrubUngated(clean(d.summary, 500)),
      recorded_at: safeDate(d.recorded_at),
    })),
    messages: (msgRows || []).map((m) => ({
      digest_id: clean(m.digest_id, 80),
      ts: safeDate(m.ts),
      channel: clean(m.channel, 24),
      author: clean(m.author, 40),
      text: scrubUngated(clean(m.text, 2000)),
      kind: clean(m.kind, 24),
      source: clean(m.source, 24),
    })),
  };
}

async function handle(request, env, params, head) {
  const path = [].concat(params.path || []);
  if (path[0] === 'status') return J(await loadStatus(env.COCKPIT_DB, new URL(request.url)), 200, head);
  if (path[0] !== 'projects' && path[0] !== 'parent-projects') return J({ error: 'not found' }, 404, head);
  // Cheap freshness probe first (read reduction): meta.updated keys the ETag
  // (every write bumps it), so a client holding the current version gets a 304
  // without the projects/subgoals/display_summaries SELECTs. The projection
  // itself is unchanged; only query order and caching moved.
  const metaRows = (await env.COCKPIT_DB.prepare('SELECT k,v FROM meta').all()).results;
  const etag = '"' + (Object.fromEntries(metaRows.map((r) => [r.k, r.v])).updated || 'empty') + '"';
  const cache = { etag, 'cache-control': 'private, no-cache' };
  const inm = request.headers.get('if-none-match') || '';
  // Cloudflare weakens the ETag (W/ prefix) when it compresses the body, so a
  // client echoes back W/"..."; compare weakly or repeat clients never get 304.
  if (inm === etag || inm === 'W/' + etag) return new Response(null, { status: 304, headers: cache });
  if (path[0] === 'projects') return J(await loadDisplay(env.COCKPIT_DB, metaRows), 200, head, cache);
  const d = await loadDisplay(env.COCKPIT_DB, metaRows);
  return J({ updated: d.updated, source_updated: d.source_updated, count: d.count,
    projects: d.projects.map((p) => ({ name: p.name, group: p.group, status: p.status, percent: p.percent, updated_at: p.updated_at })) }, 200, head, cache);
}

export async function onRequest({ request, env, params }) {
  const head = request.method === 'HEAD';
  if (!env.COCKPIT_DB) return J({ error: 'COCKPIT_DB binding missing' }, 500, head);
  if (request.method !== 'GET' && !head) return J({ error: 'method not allowed' }, 405, head);
  try {
    return await handle(request, env, params, head);
  } catch (e) {
    return unavailable(e, head);
  }
}
