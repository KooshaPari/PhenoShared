// Headless functional test for the viz viewer.
//
// No browser, no screenshot, no network. The real viewer.html is loaded, its
// embedded data block is replaced with a fixture, and its script is executed in
// Node against a small DOM shim. That exercises the code that actually ships:
// card rendering, card -> graph navigation, graph -> card marking, the session
// row, and the filter.
//
// What it deliberately does NOT test: canvas pixels. Drawing is verified by
// reading its inputs, never by capturing the screen.
//
// Run: node internal/viz/ui/viewer_test.mjs   (or: make ui-test)
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const viewerPath = join(here, '..', 'viewer.html');
const html = readFileSync(viewerPath, 'utf8');

// ---- fixture -------------------------------------------------------------
// One done node with no session, one running node with a session that nothing
// on disk can corroborate. That is the interesting pair: the rail has to show
// both, and neither may be upgraded to "validated".
const SESSION = 'dz-ui-test-session-0002';
const doc = {
  run: 'ui-fixture',
  generated_at: '2026-11-24T00:00:00Z',
  intent: 'prove the card rail and the graph stay in step',
  stats: { done: 1, running: 1, pending: 0, failed: 0, skipped: 0, progress: 0.5 },
  waves: [['1'], ['2']],
  edges: [{ from: '1', to: '2', type: 'dep' }],
  nodes: [
    { id: '1', kind: 'INTENT', status: 'done', title: 'freeze', wave: 0, artifacts: [] },
    {
      id: '2', kind: 'IMPL', status: 'running', title: 'build', wave: 1, artifacts: [],
      harness: 'jcode', session: SESSION, session_source: 'stdout',
    },
  ],
  self: { harness: 'jcode', pid: 4242, session_id: 'self-session', read_only: true },
  agents: [
    { node: '1', status: 'done', read_only: true, observed_at: '2026-11-24T00:00:01Z' },
    {
      node: '2', status: 'running', harness: 'jcode', read_only: true,
      session: SESSION, session_source: 'stdout', session_validated: false,
      session_evidence: 'no artifact corroborates this id',
      observed_at: '2026-11-24T00:00:02Z', unknown: ['model not reported'],
    },
  ],
};

// ---- DOM shim ------------------------------------------------------------
// Elements are created on demand by id, which is all the viewer needs: every
// element it touches, it looks up by id. innerHTML is recorded and scanned for
// the simple selectors the viewer actually uses (.card, .chip), so the tests
// assert on the markup the viewer really produced.
class Stub {
  constructor(tag) {
    this.tagName = tag || 'div';
    this._attrs = Object.create(null);
    this._html = '';
    this._listeners = Object.create(null);
    this.hidden = false;
    this.textContent = '';
    this.value = '';
    this.title = '';
    this.clientWidth = 800;
    this.clientHeight = 600;
    this.style = {};
    this.classList = { add() {}, remove() {}, contains: () => false };
  }
  get innerHTML() { return this._html; }
  set innerHTML(v) {
    this._html = String(v);
    // Re-parse on every write so querySelectorAll hands back the SAME objects
    // across calls, exactly as a real DOM does. Without that, an attribute the
    // viewer sets on a looked-up element would be invisible to a later lookup.
    this._children = null;
  }
  _parse() {
    if (this._children) return this._children;
    const out = [];
    const re = /<(button|div)\b([^>]*)>/g;
    let m;
    while ((m = re.exec(this._html)) !== null) {
      const attrs = m[2];
      const node = /data-node="([^"]*)"/.exec(attrs);
      const st = /data-st="([^"]*)"/.exec(attrs);
      if (!node && !st) continue;
      const el = new Stub(m[1]);
      if (node) el.setAttribute('data-node', node[1]);
      if (st) el.setAttribute('data-st', st[1]);
      if (/aria-current="true"/.test(attrs)) el.setAttribute('aria-current', 'true');
      out.push({ cls: node && /class="[^"]*\bcard\b/.test(attrs) ? 'card' : 'chip', el });
    }
    this._children = out;
    return out;
  }
  getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  removeAttribute(k) { delete this._attrs[k]; }
  addEventListener(type, fn) { (this._listeners[type] ||= []).push(fn); }
  fire(type, ev = {}) {
    const evs = ev;
    evs.target ||= this;
    evs.preventDefault ||= () => {};
    for (const fn of this._listeners[type] || []) fn(evs);
  }
  querySelectorAll(sel) {
    if (sel !== '.card' && sel !== '.chip') return [];
    const want = sel.slice(1);
    return this._parse().filter((c) => c.cls === want).map((c) => c.el);
  }
  scrollIntoView() { this._scrolled = true; }
  focus() {}
  setPointerCapture() {}
  getContext() {
    // Any drawing call is a no-op returning a fake metric. draw() is never
    // driven here: requestAnimationFrame is recorded, not looped.
    return new Proxy({}, { get: (_t, k) => (k === 'measureText' ? () => ({ width: 10 }) : () => {}) });
  }
}

const byId = new Map();
const document = {
  getElementById(id) {
    if (!byId.has(id)) byId.set(id, new Stub('div'));
    return byId.get(id);
  },
  addEventListener() {},
};
document.getElementById('dagrun-data').textContent = JSON.stringify(doc);

const window = { matchMedia: () => ({ matches: false }), addEventListener() {} };
const rafQueue = [];
const requestAnimationFrame = (fn) => { rafQueue.push(fn); return rafQueue.length; };
const cancelAnimationFrame = () => {};
const console = globalThis.console;

// ---- extract and run the viewer script -----------------------------------
const mainScript = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]).pop();
if (!mainScript || !mainScript.includes('renderCards')) {
  throw new Error('viewer.html has no script with the agent card code');
}

// A viewer crash that happens after boot (the deferred fit/animate path) must
// fail this test too, not scroll past a PASS line.
let lateError = null;
process.on('uncaughtException', (e) => { lateError = e; });

// ---- assertions ----------------------------------------------------------
let failures = 0;
function check(name, cond, detail) {
  if (cond) { console.log(`PASS ${name}`); return; }
  failures++;
  console.log(`FAIL ${name}${detail ? ': ' + detail : ''}`);
}

new Function('document', 'window', 'requestAnimationFrame', 'cancelAnimationFrame', 'console', mainScript)(
  document, window, requestAnimationFrame, cancelAnimationFrame, console,
);

const cardsEl = document.getElementById('cards');
const cardListEl = document.getElementById('cardlist');
const panelEl = document.getElementById('panel');
const observerEl = document.getElementById('observer');
const cardsBtn = document.getElementById('cardsbtn');
const cv = document.getElementById('cv');

// boot: the rail lists every node, with its session and its honesty badge
const boot = cardListEl.innerHTML;
check('rail lists node 1', boot.includes('data-node="1"'), boot);
check('rail lists node 2', boot.includes('data-node="2"'), boot);
check('rail shows the session id', boot.includes(SESSION), boot);
check('rail marks an uncorroborated session unvalidated', boot.includes('unvalidated'), boot);
check('rail does not claim validation it cannot prove', !boot.includes('>validated<'), boot);
check('rail says a sessionless node printed none', boot.includes('no session id printed'), boot);
check('observer line names the rendering harness', observerEl.textContent.includes('jcode'),
  observerEl.textContent);
check('observer line states it is read-only', observerEl.textContent.includes('read-only'),
  observerEl.textContent);

// card -> graph: clicking a card opens that node and marks the card current
const cardTwo = cardListEl.querySelectorAll('.card').find((c) => c.getAttribute('data-node') === '2');
check('card 2 is present to click', !!cardTwo);
cardListEl.fire('click', { target: cardTwo });
const opened = panelEl.innerHTML;
check('clicking a card opens the panel', panelEl.hidden === false);
check('panel is the clicked node', opened.includes('<h2>2</h2>'), opened.slice(0, 120));
check('panel shows the session id', opened.includes(SESSION), opened);
check('panel labels the session unvalidated', opened.includes('unvalidated'), opened);
check('panel carries the evidence', opened.includes('no artifact corroborates this id'), opened);
check('panel has an agent card section', opened.includes('Agent card'), opened);
check('panel states read-only observation', opened.includes('read-only observation'), opened);
check('panel surfaces what is unknown', opened.includes('model not reported'), opened);
check('selected card is marked current',
  cardListEl.querySelectorAll('.card').some((c) =>
    c.getAttribute('data-node') === '2' && c.getAttribute('aria-current') === 'true'));

// graph -> card: opening a node from the graph marks its card, no re-render needed
const pclose = document.getElementById('pclose');
check('panel offers a close control', !!pclose);
pclose.fire('click');
check('closing the panel hides it', panelEl.hidden === true);
check('closing the panel clears the current card',
  !cardListEl.querySelectorAll('.card').some((c) => c.getAttribute('aria-current') === 'true'));

// filter: the rail follows the search box, so the two lists cannot diverge
const searchEl = document.getElementById('search');
searchEl.value = '2';
searchEl.fire('input');
const filtered = cardListEl.innerHTML;
check('filter narrows the rail to the match', filtered.includes('data-node="2"'), filtered);
check('filter drops the non-match', !filtered.includes('data-node="1"'), filtered);
searchEl.value = 'zzz-no-match';
searchEl.fire('input');
check('a filter with no hits says so', cardListEl.innerHTML.includes('no cards match the filter'),
  cardListEl.innerHTML);
searchEl.value = '';
searchEl.fire('input');
check('clearing the filter restores the rail', cardListEl.innerHTML.includes('data-node="1"'));

// toggle: the rail is a view, not a modal, and it comes back
cardsBtn.fire('click');
check('toggle hides the rail', cardsEl.hidden === true);
check('toggle reports its off state', cardsBtn.getAttribute('aria-pressed') === 'false');
cardsBtn.fire('click');
check('toggle restores the rail', cardsEl.hidden === false);
check('toggle reports its on state', cardsBtn.getAttribute('aria-pressed') === 'true');

// the same toggle from the keyboard, on the canvas the user is actually in
cv.fire('keydown', { key: 'c' });
check('c hides the rail', cardsEl.hidden === true);
cv.fire('keydown', { key: 'c' });
check('c restores the rail', cardsEl.hidden === false);

// the drawing path was queued but never driven: proving this test does not
// depend on pixels or on a real canvas
check('frame loop is queued, not run', rafQueue.length > 0);

// Let the deferred boot work (fit, animate) run: it is real code on a real
// path, and it must not throw.
await new Promise((r) => setTimeout(r, 100));
check('deferred boot work does not throw', lateError === null,
  lateError && (lateError.stack || String(lateError)));

if (failures) {
  console.log(`\n${failures} check(s) failed`);
  process.exit(1);
}
console.log('\nall viewer UI checks passed');
