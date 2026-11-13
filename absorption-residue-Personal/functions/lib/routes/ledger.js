// Ledger routes: the ask register read from D1 (SQLite at the edge).
//
// The ledger's base record is the EXACT user utterance, held in reg_utterances.
// reg_asks holds the derived synthesis and points at its base.
//
// Two state axes travel with every ask: reported_state (a claim) and
// verified_state (an independent check, 'Pending review' until someone does the
// checking). Nothing here reports an ask as done on a claim alone.
//
// Read-only. Writes to the ledger go through the append-only transaction log
// and are deliberately not exposed here.

const headers = { 'content-type': 'application/json', 'cache-control': 'private, no-store' };
const reply = (body, status = 200) => new Response(JSON.stringify(body), { status, headers });

function parseList(raw) {
  try { const x = JSON.parse(raw || '[]'); return Array.isArray(x) ? x : []; } catch { return []; }
}

function row(r) {
  return {
    id: r.id,
    ask_id: r.ask_id,
    interpretation: r.interpretation,
    area: r.area,
    kind: r.kind,
    category_id: r.category_id,
    category: r.category_slug,
    category_label: r.category_label,
    first_asked_at: r.first_asked_at,
    reported_state: r.reported_state,
    verified_state: r.verified_state,
    reviewed: r.reviewed,
    reconciled_at: r.reconciled_at,
    theme_key: r.theme_key,
    issue_ref: r.issue_ref,
    issue_level: r.issue_level,
    source_missing: r.source_missing,
    // the base
    base_id: r.utterance_id,
    base_text: r.base_body,
    base_exact: r.base_exact_body,
    base_ts: r.base_ts,
    session_id: r.session_id,
    evidence: parseList(r.evidence_json),
    timeline_count: r.timeline_count,
  };
}

const ASK_SELECT = `
  SELECT a.id, a.utterance_id, a.interpretation, a.area, a.kind, a.category_id,
         a.first_asked_at, a.reported_state, a.verified_state, a.reviewed,
         a.reconciled_at, a.evidence_json, a.theme_key, a.issue_ref, a.issue_level,
         a.source_missing,
         c.slug AS category_slug, c.label AS category_label,
         u.body AS base_body, u.exact_body AS base_exact_body, u.ts AS base_ts,
         u.session_id AS session_id,
         (SELECT COUNT(*) FROM reg_transactions t WHERE t.ask_id = a.id) AS timeline_count
  FROM reg_asks a
  LEFT JOIN reg_categories c ON c.id = a.category_id
  LEFT JOIN reg_utterances u ON u.id = a.utterance_id`;

// The taxonomy is three levels deep and asks are attached to LEAF categories, so
// a parent's count is the sum over its whole subtree. Counting only direct
// children made every top-level category read 0, and selecting one filtered to
// zero asks. Both are fixed by resolving the subtree explicitly.
function buildTree(categoryRows, askCounts) {
  const nodes = new Map();
  for (const c of categoryRows) {
    nodes.set(c.id, { ...c, direct_count: askCounts.get(c.id) || 0, ask_count: 0, children: [] });
  }
  const roots = [];
  for (const n of nodes.values()) {
    if (n.parent_id && nodes.has(n.parent_id)) nodes.get(n.parent_id).children.push(n);
    else roots.push(n);
  }
  // roll counts up, deepest first
  const roll = (n) => {
    let total = n.direct_count;
    for (const ch of n.children) total += roll(ch);
    n.ask_count = total;
    return total;
  };
  for (const r of roots) roll(r);
  const sort = (list) => {
    list.sort((a, b) => (a.sort_order ?? 100) - (b.sort_order ?? 100) || a.label.localeCompare(b.label));
    list.forEach(n => sort(n.children));
  };
  sort(roots);
  return roots;
}

function subtreeIds(nodes, rootId) {
  const ids = new Set();
  const walk = (n) => {
    ids.add(n.id);
    (n.children || []).forEach(walk);
  };
  const node = nodes.get(rootId);
  if (node) walk(node);
  return ids;
}

export async function onRequest({ request, env, params }) {
  if (!['GET', 'HEAD'].includes(request.method)) return reply({ error: 'read only' }, 405);
  if (!env.COCKPIT_DB) {
    return reply({ error: 'ledger unavailable', detail: 'COCKPIT_DB is not bound on this deployment' }, 503);
  }
  const sub = ([].concat(params.path || []))[0] || '';
  const url = new URL(request.url);

  try {
    // ---- /api/ledger/categories : the drill-down tree, with rolled-up counts
    if (sub === 'categories') {
      const cats = await env.COCKPIT_DB.prepare(
        `SELECT id, parent_id, slug, label, depth, description, needs_review, sort_order
         FROM reg_categories ORDER BY sort_order, slug`).all();
      const counts = await env.COCKPIT_DB.prepare(
        `SELECT category_id, COUNT(*) AS n FROM reg_asks WHERE category_id IS NOT NULL GROUP BY category_id`).all();
      const askCounts = new Map((counts.results || []).map(r => [r.category_id, r.n]));
      const nodes = new Map((cats.results || []).map(c => [c.id, c]));
      const roots = buildTree(cats.results || [], askCounts);
      const assigned = [...askCounts.values()].reduce((a, b) => a + b, 0);
      const total = await env.COCKPIT_DB.prepare(`SELECT COUNT(*) AS n FROM reg_asks`).first();
      return reply({
        categories: roots,
        category_count: nodes.size,
        assigned_total: assigned,
        total: total ? total.n : null,
        source_mode: 'ledger',
      });
    }

    // ---- /api/ledger/ask?id=ASK-000001 : one ask, its base, its timeline
    if (sub === 'ask') {
      const id = url.searchParams.get('id');
      if (!id || !/^ASK-\d{6}$/.test(id)) return reply({ error: 'invalid id' }, 400);
      const res = await env.COCKPIT_DB.prepare(`${ASK_SELECT} WHERE a.id = ?`).bind(id).first();
      if (!res) return reply({ error: 'not found', id }, 404);
      const tx = await env.COCKPIT_DB.prepare(
        `SELECT id, ts, actor_type, actor, action, moves_state, derived, evidence_kind,
                evidence_ref, note FROM reg_transactions WHERE ask_id = ? ORDER BY ts, id`).bind(id).all();
      const msgs = await env.COCKPIT_DB.prepare(
        `SELECT m.id, m.message_id, m.role, m.seq, m.ts, m.body, m.session_id
         FROM reg_utterances m
         WHERE m.session_id = (SELECT session_id FROM reg_utterances WHERE id = ?)
         ORDER BY m.seq`).bind(res.utterance_id).all();
      const answers = await env.COCKPIT_DB.prepare(
        `SELECT id, body, ts, message_id FROM reg_answers WHERE ask_id = ? ORDER BY ts`).bind(id).all();
      return reply({
        ask: row(res),
        timeline: tx.results || [],
        session: {
          session_id: res.session_id,
          messages: msgs.results || [],
          answers: answers.results || [],
        },
        source_mode: 'ledger',
      });
    }

    // ---- /api/ledger/asks : paginated, filterable by category (with subtree)
    if (sub === 'asks' || sub === '') {
      const after = Number(url.searchParams.get('after') || 0);
      const category = url.searchParams.get('category') || '';
      const area = url.searchParams.get('area') || '';
      const q = url.searchParams.get('q') || '';
      const where = [];
      const binds = [];
      if (Number.isFinite(after) && after > 0) { where.push('a.id > ?'); binds.push(String(after)); }
      if (area) { where.push('a.area = ?'); binds.push(area); }
      if (q) { where.push('(a.interpretation LIKE ? OR u.body LIKE ?)'); binds.push(`%${q}%`, `%${q}%`); }

      if (category) {
        // Selecting a category selects its whole subtree.
        const cats = await env.COCKPIT_DB.prepare(
          `SELECT id, parent_id, slug, label, depth, description, needs_review, sort_order
           FROM reg_categories`).all();
        const counts = new Map();
        const rows = await env.COCKPIT_DB.prepare(
          `SELECT category_id, COUNT(*) AS n FROM reg_asks WHERE category_id IS NOT NULL GROUP BY category_id`).all();
        for (const r of rows.results || []) counts.set(r.category_id, r.n);
        const nodes = new Map((cats.results || []).map(c => [c.id, c]));
        const root = (cats.results || []).find(c => c.slug === category);
        if (!root) return reply({ error: 'unknown category', category }, 400);
        const ids = [...subtreeIds(nodes, root.id)];
        if (!ids.length) return reply({ error: 'unknown category', category }, 400);
        where.push(`a.category_id IN (${ids.map(() => '?').join(',')})`);
        binds.push(...ids);
      }

      const clause = where.length ? ` WHERE ${where.join(' AND ')}` : '';
      const rows = await env.COCKPIT_DB.prepare(
        `${ASK_SELECT}${clause} ORDER BY a.id LIMIT 51`).bind(...binds).all();
      const list = rows.results || [];
      const asks = list.slice(0, 50).map(row);
      const counted = await env.COCKPIT_DB.prepare(
        `SELECT COUNT(*) AS n FROM reg_asks a
         LEFT JOIN reg_utterances u ON u.id = a.utterance_id${clause.replace('a.', 'a.')}`).bind(...binds).first();
      return reply({
        asks,
        next_after: list.length > 50 ? asks.at(-1).id : null,
        total: counted ? counted.n : asks.length,
        source_mode: 'ledger',
      });
    }

    return reply({ error: 'not found', path: sub }, 404);
  } catch (err) {
    return reply({ error: 'ledger query failed', detail: String(err && err.message || err) }, 500);
  }
}
