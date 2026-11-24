import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { parseHTML } from 'linkedom';
import { counts, displayStatus, normalize } from '../src/features/jobs/model.ts';

// Jobs model: rejected is an OUTCOME on top of a completed submission.
test('rejected normalizes to sent + rejected outcome, never unknown', () => {
  const d = normalize({ updated: '2026-10-12T01:40:00-07:00', dailyTarget: '3', writeups: [], applications: [
    { company: 'A', role: 'R', status: 'rejected', date: '2026-10-05', receipt: 'https://x.test/r' },
    { company: 'B', role: 'R', status: 'sent', outcome: 'rejected', date: '2026-10-06' },
    { company: 'C', role: 'R', status: 'sent', date: '2026-10-06' },
    { company: 'D', role: 'R', status: 'weird-future-state', date: '2026-10-07' },
  ] });
  const [a, b, c, dd] = d.applications;
  // Legacy status:'rejected' row: submission happened, outcome is rejection.
  if (a.status !== 'sent' || a.outcome !== 'rejected' || displayStatus(a) !== 'rejected') throw new Error('legacy rejected row mis-modelled');
  // Explicit outcome field: honored verbatim when it says rejected.
  if (b.outcome !== 'rejected' || displayStatus(b) !== 'rejected') throw new Error('explicit outcome not honored');
  if (displayStatus(c) !== 'sent') throw new Error('plain sent row changed');
  // Unknown statuses still survive as unknown (existing safety kept).
  if (dd.status !== 'unknown' || dd.rawStatus !== 'weird-future-state') throw new Error('unknown status lost');
  const c2 = counts(d, '2026-10-06');
  if (c2.sent !== 3) throw new Error('rejected submissions must still count as sent, got ' + c2.sent);
  if (c2.rejected !== 2) throw new Error('rejected outcome count wrong, got ' + c2.rejected);
  // Ambiguous notices never become rejections.
  const e = normalize({ updated: '', dailyTarget: '', applications: [{ company: 'E', status: 'sent', note: 'we regret to inform you...' }] });
  if (e.applications[0].outcome === 'rejected') throw new Error('rejection invented from a note');
});

// Projects page (built artifact): percent clamping, ungrouped fallback, freshness.
const distHtml = readFileSync(new URL('../dist/projects/index.html', import.meta.url), 'utf8');
const inlineScript = [...distHtml.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).find(s => s.includes('/api/display/projects')) ?? '';
async function renderPage(data: unknown) {
  const { document } = parseHTML(distHtml);
  const fetchStub = async () => ({ ok: true, json: async () => data });
  new Function('document', 'fetch', inlineScript)(document, fetchStub);
  await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  return document;
}
test('projects page clamps percent into 0..100 for width and aria-valuenow', async () => {
  const doc = await renderPage({ updated: '2026-10-15T12:00:00-07:00', projects: [
    { group: 'G', name: 'over', status: 'active', percent: 150, needs_review: true, subgoal_count: 0 },
    { group: 'G', name: 'under', status: 'active', percent: -5, needs_review: true, subgoal_count: 0 },
    { group: 'G', name: 'junk', status: 'active', percent: 'abc', needs_review: true, subgoal_count: 0 },
    { group: 'G', name: 'zero', status: 'active', percent: 0, needs_review: true, subgoal_count: 0 },
    { group: 'G', name: 'nullpct', status: 'active', percent: null, needs_review: true, subgoal_count: 0 },
    { group: 'G', name: 'blank', status: 'active', percent: '   ', needs_review: true, subgoal_count: 0 },
    { group: 'G', name: 'boolpct', status: 'active', percent: true, needs_review: true, subgoal_count: 0 },
    { group: '', name: 'nogroup', status: 'mystery-status', needs_review: true, subgoal_count: 0 },
  ] });
  const bars = [...doc.querySelectorAll('.project-bar')];
  const over = bars.find(b => b.getAttribute('aria-label') === 'over progress');
  if (!over || over.getAttribute('aria-valuenow') !== '100') throw new Error('150 not clamped to 100 in aria');
  if (!(over.querySelector('.project-fill')?.getAttribute('style') ?? '').includes('100%')) throw new Error('150 not clamped in width');
  const under = bars.find(b => b.getAttribute('aria-label') === 'under progress');
  if (!under || under.getAttribute('aria-valuenow') !== '0') throw new Error('-5 not clamped to 0');
  if ([...doc.querySelectorAll('.project-bar')].some(b => b.getAttribute('aria-label') === 'junk progress')) throw new Error('non-numeric percent rendered a bar');
  const zero = bars.find(b => b.getAttribute('aria-label') === 'zero progress');
  if (!zero || zero.getAttribute('aria-valuenow') !== '0') throw new Error('real 0% must render as 0, not vanish as unknown');
  if (!(zero.querySelector('.project-fill')?.getAttribute('style') ?? '').includes('width:0%')) throw new Error('real 0% width missing');
  for (const unknown of ['nullpct', 'blank', 'boolpct']) {
    if (bars.some(b => b.getAttribute('aria-label') === unknown + ' progress')) throw new Error(unknown + ' fabricated a progress bar');
    const card = [...doc.querySelectorAll('.project')].find(c => (c.textContent ?? '').includes(unknown));
    if (card && (card.textContent ?? '').includes('%')) throw new Error(unknown + ' card shows a fabricated percentage');
  }
  if (!doc.querySelector('#ungrouped')) throw new Error('missing group did not fall back to Ungrouped');
  if (!doc.body.textContent.includes('mystery-status')) throw new Error('unknown status not shown verbatim');
  const fresh = doc.querySelector('#freshness')?.textContent ?? '';
  if (!fresh.includes('Source updated') || !fresh.includes('fetched')) throw new Error('freshness must separate source time from fetch time: ' + fresh);
});

// Parent page (built artifact): History heading precedes the snapshot tiles; live feed never fabricates 0%.
const parentHtml = readFileSync(new URL('../dist/parent/index.html', import.meta.url), 'utf8');
test('parent History heading sits above the snapshot summary tiles', () => {
  const h = parentHtml.indexOf('<h2 class="parent-history"'), s = parentHtml.indexOf('<section class="parent-summary"');
  if (h === -1 || s === -1 || h > s) throw new Error('History heading element must come before the snapshot summary section');
});
test('parent live projects treat unknown percent as unknown, never 0', async () => {
  const script = [...parentHtml.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).find(x => x.includes('/api/display/parent-projects')) ?? '';
  if (!script) throw new Error('parent live script not found in built page');
  const { document } = parseHTML(parentHtml);
  const fetchStub = async () => ({ ok: true, json: async () => ({ updated: '2026-10-15T12:00:00-07:00', projects: [
    { group: 'G', name: 'realzero', status: 'active', percent: 0 },
    { group: 'G', name: 'unknownpct', status: 'active', percent: null },
    { group: 'G', name: 'blankpct', status: 'active', percent: '  ' },
  ] }) });
  new Function('document', 'fetch', script)(document, fetchStub);
  await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  const cards = [...document.querySelectorAll('.parent-live-card')];
  const zero = cards.find(c => (c.textContent ?? '').includes('realzero'));
  if (!zero || !(zero.textContent ?? '').includes('0%')) throw new Error('real 0% must display as 0%');
  for (const name of ['unknownpct', 'blankpct']) {
    const card = cards.find(c => (c.textContent ?? '').includes(name));
    if (!card) throw new Error(name + ' card missing');
    if ((card.textContent ?? '').includes('%')) throw new Error(name + ' shows a fabricated percentage');
  }
});

test('projects page shows an explicit zero-row empty state', async () => {
  const doc = await renderPage({ updated: '2026-10-15T12:00:00-07:00', projects: [] });
  if (!doc.querySelector('.projects-empty')) throw new Error('empty state element missing');
  if (doc.querySelectorAll('.project').length !== 0) throw new Error('phantom project cards rendered');
  if (doc.querySelectorAll('.project-bar').length !== 0) throw new Error('phantom progress bars rendered');
});
test('parent labels record mutation vs metadata verification and timestamps the fetch', async () => {
  const script = [...parentHtml.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).find(x => x.includes('/api/display/parent-projects')) ?? '';
  const { document } = parseHTML(parentHtml);
  const fetchStub = async () => ({ ok: true, json: async () => ({ updated: '2026-10-08T09:00:00-07:00', source_updated: '2026-10-15T11:30:00-07:00', projects: [
    { group: 'G', name: 'p1', status: 'active', percent: 40, updated_at: '2026-10-15T11:30:00-07:00' },
  ] }) });
  new Function('document', 'fetch', script)(document, fetchStub);
  await new Promise(r => setTimeout(r, 0)); await new Promise(r => setTimeout(r, 0));
  const meta = document.getElementById('live-meta')?.textContent ?? '';
  if (!meta.includes('Records last changed') || !meta.includes('(mutation time, not a verification date)')) throw new Error('mutation time not labeled honestly: ' + meta);
  if (!meta.includes('Oct 15, 2026')) throw new Error('mutation cutoff should come from record timestamps: ' + meta);
  if (!meta.includes('global metadata timestamp') || !meta.includes('Oct 8, 2026')) throw new Error('global metadata timestamp not shown: ' + meta);
  if (meta.toLowerCase().includes('verified')) throw new Error('verification claim must not appear: ' + meta);
  if (!meta.includes('(load-time check)')) throw new Error('fetch must be labeled a timestamped load-time check: ' + meta);
  if (meta.includes('fetched just now')) throw new Error('evergreen fetched-just-now claim remains');
});
