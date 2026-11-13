// The ask register, served from the ledger in D1 (SQLite at the edge).
//
// Source of truth is the ledger: reg_asks holds the derived synthesis and
// reg_utterances holds the EXACT user utterance that ask came from. That
// matters because the register's own `original_text` was a truncated fragment;
// `original_text` below is now the verbatim message body.
//
// Fallback order:
//   ledger      - D1 ledger (the full register, 2,259 asks)
//   inventory   - the static asset, same data, no D1 needed
//   snapshot    - the old baked-in snapshot, last resort
//
// Two state axes travel with every ask: reported_state (a claim) and
// verified_state (an independent check). verified_state stays
// 'Pending review' until someone actually reviews it.

const headers = { 'content-type': 'application/json', 'cache-control': 'private, no-store' };
const reply = (body, status = 200) => new Response(JSON.stringify(body), { status, headers });
const SNAPSHOT_CAPTURED_AT = "2026-10-16T20:58:00Z";
const SNAPSHOT = [{"id": 1, "original_text": "Take a look at atoms bot as well we will probably want to merge and extend the feature", "interpretation": "AtomsBot repo hunt / restore old AtomsTech variant", "first_asked_at": "Sunday, October 11, 2026, 2:23:16 PM PDT", "reported_state": "DONE", "verified_state": "Pending review", "task_links_json": "[]", "source_refs_json": "[{\"kind\": \"original user message\", \"at\": \"Sunday, October 11, 2026, 2:23:16 PM PDT\"}]", "reconciled_at": null, "updated_at": "2026-10-16T20:58:10.903351+00:00", "reviewed": 1}, {"id": 2, "original_text": "Been almost 24hrs, really no export? Do you even have receipt confirmation for the request?", "interpretation": "ChatGPT + Gemini + Claude data exports", "first_asked_at": "Friday, October 9, 2026, 11:48:08 PM PDT", "reported_state": "DONE", "verified_state": "Pending review", "task_links_json": "[]", "source_refs_json": "[{\"kind\": \"original user message\", \"at\": \"Friday, October 9, 2026, 11:48:08 PM PDT\"}]", "reconciled_at": null, "updated_at": "2026-10-16T20:58:10.903395+00:00", "reviewed": 1}, {"id": 3, "original_text": "Draft access request and note of suspiciously designed failing request for data", "interpretation": "CCPA/DSAR access-request draft vs OpenAI", "first_asked_at": "Saturday, October 10, 2026, 12:14:27 AM PDT", "reported_state": "DEFERRED-BY-HIM", "verified_state": "Pending review", "task_links_json": "[]", "source_refs_json": "[{\"kind\": \"original user message\", \"at\": \"Saturday, October 10, 2026, 12:14:27 AM PDT\"}]", "reconciled_at": null, "updated_at": "2026-10-16T20:58:10.903407+00:00", "reviewed": 1}, {"id": 4, "original_text": "Browser Automation Mark as done and moved to local", "interpretation": "'Browser Automation' chat marked done + moved local", "first_asked_at": "Friday, October 9, 2026, 12:39:15 AM PDT", "reported_state": "DONE", "verified_state": "Pending review", "task_links_json": "[]", "source_refs_json": "[{\"kind\": \"original user message\", \"at\": \"Friday, October 9, 2026, 12:39:15 AM PDT\"}]", "reconciled_at": null, "updated_at": "2026-10-16T20:58:10.903416+00:00", "reviewed": 1}];

const LEDGER_SELECT = `
  SELECT a.id, a.interpretation, a.first_asked_at, a.reported_state, a.verified_state,
         a.reconciled_at, a.updated_at, a.evidence_json, a.area, a.kind,
         a.theme_key, a.issue_ref, a.issue_level, a.source_missing,
         c.slug AS category_slug, c.label AS category_label,
         u.body AS base_body, u.exact_body AS base_exact_body, u.ts AS base_ts,
         (SELECT COUNT(*) FROM reg_transactions t WHERE t.ask_id = a.id) AS timeline_count
  FROM reg_asks a
  LEFT JOIN reg_categories c ON c.id = a.category_id
  LEFT JOIN reg_utterances u ON u.id = a.utterance_id`;

function parseList(raw) {
  try { const x = JSON.parse(raw || '[]'); return Array.isArray(x) ? x : []; } catch { return []; }
}

// Map a ledger row onto the shape the page already renders, so the existing
// UI keeps working and gains the ledger's extra fields.
function ledgerRow(r) {
  return {
    id: r.id,
    original_text: r.base_body || null,
    interpretation: r.interpretation,
    first_asked_at: r.first_asked_at,
    reported_state: r.reported_state,
    verified_state: r.verified_state,
    task_links: [],
    source_refs: r.base_ts ? [{ kind: 'original user message', at: r.base_ts }] : [],
    reconciled_at: r.reconciled_at,
    updated_at: r.updated_at,
    evidence: parseList(r.evidence_json),
    area: r.area,
    kind: r.kind,
    category: r.category_slug,
    category_label: r.category_label,
    theme_key: r.theme_key,
    issue_ref: r.issue_ref,
    issue_level: r.issue_level,
    source_missing: r.source_missing,
    base_exact: r.base_exact_body,
    timeline_count: r.timeline_count,
  };
}

export async function onRequest({ request, env, params }) {
  if (!['GET', 'HEAD'].includes(request.method)) return reply({ error: 'read only' }, 405);
  if ([].concat(params.path || []).length) return reply({ error: 'not found' }, 404);
  const url = new URL(request.url);
  const raw = url.searchParams.get('after') || '0';
  if (!/^\d{1,12}$/.test(raw)) return reply({ error: 'invalid cursor' }, 400);
  const after = Number(raw);

  const snapshot = () => page(SNAPSHOT.filter(r => r.id > after).slice(0, 51), 'snapshot', request.method);

  // ---- ledger (D1) ----
  if (env.COCKPIT_DB) {
    try {
      const rows = await env.COCKPIT_DB.prepare(
        `${LEDGER_SELECT} WHERE a.id > ? ORDER BY a.id LIMIT 51`).bind(String(after)).all();
      if (rows.results && rows.results.length) {
        return page(rows.results.map(ledgerRow), 'ledger', request.method);
      }
      // Bound but empty: fall through to the static inventory rather than
      // showing nothing, so a half-populated D1 never hides the register.
    } catch { /* fall through to the static asset */ }
  }

  // ---- static inventory asset ----
  try {
    if (env.ASSETS) {
      const res = await env.ASSETS.fetch(new URL('/asks/inventory.json', request.url));
      if (res.ok) {
        const doc = await res.json();
        if (Array.isArray(doc.asks)) {
          const rows = doc.asks.filter(r => Number(r.id) > after).slice(0, 51);
          return page(rows, 'inventory', request.method, doc);
        }
      }
    }
  } catch { /* fall through to the snapshot */ }

  return snapshot();
}

function page(rows, sourceMode, method, doc) {
  const asks = rows.slice(0, 50).map(r => (sourceMode === 'ledger' ? r : ({
    id: r.id,
    original_text: r.original_text,
    interpretation: r.interpretation,
    first_asked_at: r.first_asked_at,
    reported_state: r.reported_state,
    verified_state: r.verified_state,
    task_links: parseList(r.task_links_json),
    source_refs: parseList(r.source_refs_json),
    reconciled_at: r.reconciled_at,
    updated_at: r.updated_at,
  })));
  if (method === 'HEAD') return new Response(null, { headers });
  const notes = {
    ledger: 'Ledger: the full register from D1. Original text is the verbatim message; the ask is the derived reading. Verification remains per ask and is not completion proof.',
    inventory: 'Unreviewed inventory of the full register. Recorded, not reviewed, not a completion ledger. Verbatim message text is excluded.',
    snapshot: 'Saved snapshot, not live database state. All verification remains pending review.',
  };
  return reply({
    asks,
    next_after: rows.length > 50 ? asks.at(-1).id : null,
    source_mode: sourceMode,
    total: sourceMode === 'inventory' ? (doc && doc.count) || null : sourceMode === 'ledger' ? asks.length : null,
    snapshot_captured_at: sourceMode === 'snapshot' ? SNAPSHOT_CAPTURED_AT : null,
    note: notes[sourceMode] || null,
  });
}
