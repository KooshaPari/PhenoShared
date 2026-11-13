import { counts, displayStatus, fetchedLabel, labels, normalize, receiptUrl, revision, statuses, updatedLabel, type AnswerRow, type Application, type Decision, type Jobs, type Status, type Writeup } from './model';
const el = (id: string) => document.getElementById(id)!;
function node(tag: string, className = '', value = '') { const n = document.createElement(tag); n.className = className; n.textContent = value; return n; }
type Display = Status | 'rejected';
const displayOrder: Display[] = ['sent', 'rejected', 'tap', 'held', 'skipped', 'blocked', 'unknown'];
let data: Jobs | undefined, filter: Display | 'all' = 'all', labelTimer: ReturnType<typeof setInterval> | undefined, dataTimer: ReturnType<typeof setInterval> | undefined, loading = false, lastFetch = 0, refreshFailed = false;
let answers = new Map<string, AnswerRow[]>(), answersOk = false, revisions = new Map<string, string>();
function state(target: string, message: string, error = false) { const n = node('div', 'jobs-state' + (error ? ' jobs-error' : ''), message); if (error) { n.setAttribute('role', 'alert'); const b = node('button', 'cockpit-control', 'Retry'); b.setAttribute('type', 'button'); b.onclick = () => load(); n.append(node('div', 'jobs-actions')); n.lastChild!.appendChild(b); } el(target).replaceChildren(n); }
function freshness() {
  const upd = data?.updated;
  const source = upd ? new Date(upd) : new Date(NaN);
  const sourceOk = Number.isFinite(source.getTime());
  const sourceText = sourceOk
    ? 'Source snapshot ' + source.toLocaleString('en-US', { timeZone: 'America/Los_Angeles', dateStyle: 'medium', timeStyle: 'short' }) + ' PT (static file - live sync pending)'
    : 'Source update time unavailable (static file - live sync pending)';
  el('updated').textContent = sourceText + ' · ' + (lastFetch ? fetchedLabel(lastFetch) : 'not checked yet') + (refreshFailed ? ' · last refresh failed - showing the previous snapshot' : '');
  el('updated').title = sourceOk ? 'Source data ' + source.toLocaleString() : '';
}
function renderSummary() {
  const c = counts(data!), tiles = [['Sent total', c.sent, 'Confirmed submissions'], ['Sent today', c.today, 'Local calendar day'], ['Rejected', c.rejected, 'Latest outcome'], ['Needs your tap', c.tap, 'Manual action needed'], ['Daily target', data!.dailyTarget, 'Steady, thoughtful progress']];
  el('summary').replaceChildren(...tiles.map(([label, value, hint]) => { const card = node('div', 'cockpit-card'); card.append(node('span', 'jobs-label', String(label)), node('strong', 'jobs-value', String(value)), node('span', 'jobs-label', String(hint))); return card; }));
}
function renderFilters() {
  el('filters').replaceChildren(...(['all', ...displayOrder] as const).map(s => {
    const n = s === 'all' ? data!.applications.length : data!.applications.filter(a => displayStatus(a) === s).length;
    const b = node('button', 'cockpit-control', `${s === 'all' ? 'All' : labels[s]} (${n})`); b.setAttribute('type', 'button'); b.dataset.filter = s; b.setAttribute('aria-pressed', String(filter === s));
    b.onclick = () => { filter = s; renderFilters(); renderApps(); el('filters').querySelector<HTMLButtonElement>(`[data-filter="${s}"]`)?.focus(); }; return b;
  }));
}
function application(a: Application) {
  const shown = displayStatus(a), card = node('article', 'cockpit-card'), top = node('div', 'jobs-cardtop'), title = node('div'); title.append(node('div', 'jobs-company', a.company || 'Company unavailable'), node('div', 'jobs-role', a.role || 'Role unavailable'));
  top.append(title, node('span', 'jobs-badge ' + shown, shown === 'rejected' ? 'Rejected' : a.rawStatus || 'Unknown')); card.append(top);
  if (a.outcome === 'rejected' && a.status === 'sent') card.append(node('p', 'jobs-note', 'Application was submitted; the latest outcome is rejection.'));
  const details = [a.location, a.route, a.date].filter(Boolean); if (details.length) { const d = node('div', 'jobs-details'); details.forEach(value => d.append(node('span', '', value))); card.append(d); }
  if (a.note) card.append(node('p', 'jobs-note', a.note)); const url = receiptUrl(a.receipt);
  if (url) { const link = node('a', 'cockpit-control jobs-receipt', 'View receipt') as HTMLAnchorElement; link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link); } return card;
}
function renderApps() {
  const items = data!.applications.filter(a => filter === 'all' || displayStatus(a) === filter); el('appCount').textContent = `${items.length} ${items.length === 1 ? 'application' : 'applications'}`;
  if (!items.length) { state('apps', filter === 'all' ? 'No applications yet. Your next step will show up here.' : `No ${labels[filter].toLowerCase()} applications right now.`); return; }
  el('apps').replaceChildren(...displayOrder.filter(s => items.some(a => displayStatus(a) === s)).map(s => { const group = node('section', 'jobs-group'); group.setAttribute('aria-label', labels[s] + ' applications'); const subset = items.filter(a => displayStatus(a) === s), cards = node('div', 'jobs-cards'); group.append(node('h3', '', `${labels[s]} · ${subset.length}`)); cards.append(...subset.map(application)); group.append(cards); return group; }));
}
// Write-ups carry decisions. The default mirrors the long-standing write-up approval pair;
// decision cards declare their own options or factual questions in status.json.
const DEFAULT_DECISION: Decision = { type: 'choice', options: [{ key: 'approve', label: 'Approve' }, { key: 'changes', label: 'Request changes' }] };
function decisionOf(w: Writeup): Decision | null {
  if (w.decision === null) return null; // explicitly closed: decided/answered/deferred - never controls
  return w.decision === undefined ? DEFAULT_DECISION : w.decision;
}
function latestAnswer(id: string): AnswerRow | undefined { const rows = answers.get(id); return rows && rows.length ? rows[rows.length - 1] : undefined; }
function answerLabel(w: Writeup, a: AnswerRow): string {
  const d = decisionOf(w);
  if (a.answer_type === 'choice' && d && d.type === 'choice') return d.options.find(o => o.key === a.choice)?.label || a.choice || '';
  if (a.answer_type === 'facts') return `factual answers (${a.facts?.length || 0})`;
  return a.choice || '';
}
function decisionBlock(w: Writeup): HTMLElement {
  const wrap = node('div', 'jobs-decision');
  const rev = revisions.get(w.id) || '';
  if (!w.id) { wrap.append(node('p', 'jobs-note', 'Answer capture is unavailable for this card (no card id).')); return wrap; }
  if (!answersOk) {
    const note = node('p', 'jobs-note', 'Answer recording is unavailable right now - nothing clicked here can be saved. Reload to retry.');
    wrap.append(note); return wrap;
  }
  const recorded = latestAnswer(w.id);
  if (recorded) {
    const when = new Date(recorded.created_at).toLocaleString('en-US', { timeZone: 'America/Los_Angeles', dateStyle: 'medium', timeStyle: 'short' });
    const current = recorded.revision === rev;
    wrap.append(node('p', 'jobs-answer' + (current ? '' : ' jobs-answer-stale'),
      current ? `Recorded: ${answerLabel(w, recorded)} - ${when} PT (you). Answering again updates this.` :
        `Earlier answer (${answerLabel(w, recorded)}, ${when} PT) was for a previous version of this card - please re-read and answer again.`));
  }
  const d = decisionOf(w);
  if (d === null) {
    wrap.append(node('p', 'jobs-note jobs-closed', 'Decided - retained for history. No answer pending; this card is not accepting responses.'));
    return wrap;
  }
  const controls: (HTMLButtonElement | HTMLTextAreaElement)[] = [];
  const fail = (msg: string) => { const e = node('p', 'jobs-note jobs-error', msg); e.setAttribute('role', 'alert'); wrap.append(e); };
  const done = () => { void refreshAnswers().then(renderWriteups); };
  if (d.type === 'choice') {
    const actions = node('div', 'jobs-actions');
    d.options.forEach((opt, i) => {
      const b = node('button', 'cockpit-control' + (i === 0 ? ' jobs-action-primary' : ''), opt.label) as HTMLButtonElement;
      b.setAttribute('type', 'button'); controls.push(b);
      b.onclick = () => { controls.forEach(c => { c.disabled = true; }); void postAnswer({ card_id: w.id, revision: rev, type: 'choice', choice: opt.key }).then(r => { if (r.ok) done(); else { fail(r.error || 'Could not record the answer. Try again.'); controls.forEach(c => { c.disabled = false; }); } }); };
      actions.append(b);
    });
    wrap.append(actions);
  } else {
    const form = node('div', 'jobs-facts'), boxes = new Map<string, HTMLTextAreaElement>();
    d.questions.forEach(q => {
      form.append(node('label', 'jobs-label', q.label));
      const t = node('textarea', 'jobs-fact') as HTMLTextAreaElement; t.rows = 2; t.setAttribute('aria-label', q.label); controls.push(t); boxes.set(q.key, t); form.append(t);
    });
    const actions = node('div', 'jobs-actions');
    const b = node('button', 'cockpit-control jobs-action-primary', 'Submit answers') as HTMLButtonElement; b.setAttribute('type', 'button'); controls.push(b);
    b.onclick = () => {
      const facts = d.questions.map(q => ({ key: q.key, text: (boxes.get(q.key)?.value || '').trim() }));
      if (facts.some(f => !f.text)) { fail('Every question needs an answer before it can be recorded.'); return; }
      controls.forEach(c => { c.disabled = true; });
      void postAnswer({ card_id: w.id, revision: rev, type: 'facts', facts }).then(r => { if (r.ok) done(); else { fail(r.error || 'Could not record the answers. Try again.'); controls.forEach(c => { c.disabled = false; }); } });
    };
    actions.append(b); form.append(actions); wrap.append(form);
  }
  return wrap;
}
async function postAnswer(body: Record<string, unknown>): Promise<{ ok: boolean; error?: string }> {
  try {
    const r = await fetch('/api/answers', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    if (r.status === 401 || r.status === 403) return { ok: false, error: 'Your sign-in could not be verified. Refresh the page and try again.' };
    const d = await r.json().catch(() => ({}));
    return r.ok ? { ok: true } : { ok: false, error: typeof d.error === 'string' ? d.error : 'The answer service rejected the save.' };
  } catch { return { ok: false, error: 'The answer service is unreachable. Check the connection and try again.' }; }
}
async function refreshAnswers(): Promise<void> {
  const testMode = new URLSearchParams(location.search).get('test') === '1';
  const r = await fetch(testMode ? '/api/answers?include_test=1' : '/api/answers', { cache: 'no-store' });
  if (!r.ok) { answersOk = false; return; }
  const d = await r.json();
  answers = new Map();
  for (const a of d.answers || []) { const rows = answers.get(a.card_id) || []; rows.push(a); answers.set(a.card_id, rows); }
  answersOk = true;
}
function renderWriteups() {
  const showTest = new URLSearchParams(location.search).get('test') === '1';
  const visible = data!.writeups.filter(w => showTest || !w.test);
  const openCount = visible.filter(w => w.decision !== null).length;
  el('writeCount').textContent = openCount === visible.length ? `${openCount} waiting` : `${openCount} waiting - ${visible.length - openCount} decided`; if (!visible.length) { state('writeups', 'Nothing waiting for approval. New drafts will appear here.'); return; }
  el('writeups').replaceChildren(...visible.map(w => { const card = node('article', 'cockpit-card'); card.append(node('div', 'jobs-company', w.company || 'Company unavailable')); if (w.role) card.append(node('div', 'jobs-role', w.role)); const raw = w.text || 'Draft text unavailable';
    if (w.decision === null) {
      const cut = raw.indexOf('\n\n');
      card.append(node('pre', 'jobs-writeup', cut > 0 ? raw.slice(0, cut) : raw));
      if (cut > 0) {
        const det = node('details', 'jobs-history') as HTMLDetailsElement;
        det.append(node('summary', '', 'Original card text (historical - decision recorded above)'));
        det.append(node('pre', 'jobs-writeup', raw.slice(cut + 2)));
        card.append(det);
      }
    } else { card.append(node('pre', 'jobs-writeup', raw)); }
    card.append(decisionBlock(w)); return card; }));
}
async function load(options: { silent?: boolean } = {}) {
  const silent = options.silent === true && data !== undefined;
  if (loading) return; loading = true;
  if (!silent) { clearInterval(labelTimer); el('jobs').setAttribute('aria-busy', 'true'); el('updated').textContent = 'Loading update time…'; el('summary').replaceChildren(); el('filters').replaceChildren(); el('appCount').textContent = ''; el('writeCount').textContent = ''; state('apps', 'Loading applications…'); state('writeups', 'Loading drafts…'); }
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
  try { const r = await fetch('./status.json', { cache: 'no-store', signal: controller.signal }); if (!r.ok) throw new Error(`HTTP ${r.status}`);
    data = normalize(await r.json()); lastFetch = Date.now(); refreshFailed = false;
    revisions = new Map(await Promise.all(data.writeups.map(async w => [w.id, await revision(w)] as [string, string])));
    await refreshAnswers();
    freshness(); renderSummary(); renderFilters(); renderApps(); renderWriteups();
    // One label timer, one data timer - never stacked, on EVERY successful fetch
    // regardless of entry path (initial, manual refresh, or silent refetch). The
    // data timer re-fetches the source; the label timer only re-renders the
    // "checked N minutes ago" text.
    clearInterval(labelTimer); labelTimer = setInterval(freshness, 60000);
    if (!dataTimer) dataTimer = setInterval(() => { void load({ silent: true }); }, 300000);
  } catch { if (silent) { refreshFailed = true; freshness(); } else { el('updated').textContent = 'Status unavailable'; state('apps', 'Could not load valid status.json. Check the connection and retry.', true); state('writeups', 'Drafts unavailable until status loads.'); } }
  finally { clearTimeout(timeout); loading = false; el('jobs').setAttribute('aria-busy', 'false'); }
}
document.getElementById('refresh')?.addEventListener('click', () => { void load({ silent: true }); });
void load();
