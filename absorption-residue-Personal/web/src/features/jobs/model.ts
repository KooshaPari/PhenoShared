export const statuses = ['sent', 'tap', 'held', 'skipped', 'blocked', 'unknown'] as const;
export type Status = typeof statuses[number];
// Latest OUTCOME is tracked separately from the submission status above: a
// submitted application can later be rejected, and rejected is not skipped,
// held or sent. Only explicit outcome data sets this - never inferred.
export type Outcome = 'rejected' | '';
export const labels: Record<string, string> = { sent: 'Sent', tap: 'Needs your tap', held: 'Held', skipped: 'Skipped', blocked: 'Blocked', unknown: 'Other / unknown', rejected: 'Rejected' };
export type Application = Record<'company' | 'role' | 'location' | 'route' | 'date' | 'note' | 'receipt', string> & { status: Status; rawStatus: string; outcome: Outcome; outcomeRaw: string };
export type DecisionOption = { key: string; label: string };
export type Decision = { type: 'choice'; options: DecisionOption[] } | { type: 'facts'; questions: DecisionOption[] };
export type Writeup = { company: string; role: string; text: string; id: string; decision?: Decision | null | undefined; test?: boolean };
export type AnswerRow = { id: number; card_id: string; revision: string; answer_type: string; choice: string | null; facts: { key: string; text: string }[] | null; identity: string; created_at: string; test: boolean };
export type Jobs = { updated: string; dailyTarget: string; applications: Application[]; writeups: Writeup[] };
export const text = (v: unknown): string => typeof v === 'string' || typeof v === 'number' && Number.isFinite(v) ? String(v) : '';
function record(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Error('Expected a record in status.json.');
  return v as Record<string, unknown>;
}
function list(v: unknown, field: string, optional = false): unknown[] {
  if ((v === undefined || v === null) && optional) return [];
  if (!Array.isArray(v)) throw new Error(`status.json ${field} must be an array.`);
  return v;
}
// What the card, filters and grouping show: the latest outcome wins over the
// submission state, so a rejected application reads Rejected, not Sent and
// never vanishes into Other / unknown.
export function displayStatus(a: Application): Status | 'rejected' {
  return a.outcome === 'rejected' ? 'rejected' : a.status;
}
export function normalize(value: unknown): Jobs {
  const d = record(value);
  return { updated: text(d.updated), dailyTarget: text(d.dailyTarget) || '—',
    applications: list(d.applications, 'applications').map(value => {
      const a = record(value), rawStatus = text(a.status), outcomeRaw = text(a.outcome);
      // Legacy rows used status:'rejected' for what is an outcome: the
      // submission happened (receipt/date exist), the outcome is rejection.
      let status: Status = statuses.includes(rawStatus as Status) ? rawStatus as Status : 'unknown';
      let outcome: Outcome = outcomeRaw.toLowerCase() === 'rejected' ? 'rejected' : '';
      if (rawStatus === 'rejected') { status = 'sent'; outcome = 'rejected'; }
      return { company: text(a.company), role: text(a.role), location: text(a.location), route: text(a.route), date: text(a.date), note: text(a.note), receipt: text(a.receipt), status, rawStatus, outcome, outcomeRaw };
    }), writeups: list(d.writeups, 'writeups', true).map(value => {
      const w = record(value); return { company: text(w.company), role: text(w.role), text: text(w.text), id: text(w.id), decision: decision(w.decision), test: w.test === true };
    }) };
}
export function receiptUrl(value: unknown): string | null {
  const raw = text(value), match = raw.match(/^\[([^\]]+)\]\((https:\/\/[^\s)]+)\)$/), candidate = match ? match[2] : raw;
  try { const u = new URL(candidate); return u.protocol === 'https:' && !u.username && !u.password ? u.href : null; } catch { return null; }
}
function options(v: unknown): DecisionOption[] {
  if (!Array.isArray(v)) return [];
  return v.map(o => (!o || typeof o !== 'object' || Array.isArray(o) ? { key: '', label: '' } : { key: text((o as Record<string, unknown>).key), label: text((o as Record<string, unknown>).label) })).filter(o => o.key && o.label);
}
// Card decisions are recorded server-side (api/answers) with the exact card revision they
// answered; the earlier sms: draft links had no recipient and no consumer and were removed.
export function decision(v: unknown): Decision | null | undefined {
  // undefined = field absent (active card: default controls apply); null = explicitly closed (decided/answered/deferred: no controls).
  if (v === undefined) return undefined;
  if (!v || typeof v !== 'object' || Array.isArray(v)) return null;
  const d = v as Record<string, unknown>, t = text(d.type);
  if (t === 'choice') { const o = options(d.options); return o.length ? { type: 'choice', options: o } : null; }
  if (t === 'facts') { const q = options(d.questions); return q.length ? { type: 'facts', questions: q } : null; }
  return null;
}
// The revision binds an answer to the exact card content the owner read. Any change to
// company, role, text or the decision config yields a new revision; answers to older
// revisions stay in the ledger and render as superseded.
export async function revision(w: Writeup): Promise<string> {
  const basis = JSON.stringify([w.company, w.role, w.text, w.decision]);
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(basis));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}
export function localDay(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
export function counts(data: Jobs, day = localDay()) {
  return { sent: data.applications.filter(a => a.status === 'sent').length, today: data.applications.filter(a => a.status === 'sent' && a.date === day).length, tap: data.applications.filter(a => a.status === 'tap').length, rejected: data.applications.filter(a => a.outcome === 'rejected').length };
}
export function updatedLabel(value: string, now = Date.now()): string {
  const date = value ? new Date(value) : new Date(NaN);
  if (!Number.isFinite(date.getTime())) return 'Updated time unavailable';
  const seconds = Math.max(0, Math.floor((now - date.getTime()) / 1000));
  if (seconds < 60) return 'Updated just now';
  const n = Math.floor(seconds / (seconds < 3600 ? 60 : seconds < 86400 ? 3600 : 86400));
  const unit = seconds < 3600 ? 'minute' : seconds < 86400 ? 'hour' : 'day';
  return `Updated ${n} ${unit}${n === 1 ? '' : 's'} ago`;
}
export function fetchedLabel(since: number, now = Date.now()): string {
  const seconds = Math.max(0, Math.floor((now - since) / 1000));
  if (seconds < 60) return 'checked just now';
  const n = Math.floor(seconds / 60);
  return `checked ${n} minute${n === 1 ? '' : 's'} ago`;
}