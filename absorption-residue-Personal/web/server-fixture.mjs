import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { join, extname } from 'node:path';
const ROOT = './dist';
const MODE = process.env.FIXTURE_MODE || 'populated';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.ico': 'image/x-icon' };
const populated = { updated: '2026-10-08T09:00:00-07:00', source_updated: '2026-10-15T11:30:00-07:00', note: '', count: 3, projects: [
  { id: 1, name: 'Alpha', group: 'G1', status: 'active', percent: 40, detail: 'alpha detail', next: 'ship it', eta: '2d', blocker: '', usable: 'yes', subgoals: [{ name: 's1', state: 'done' }, { name: 's2', state: 'open' }], updated_at: '2026-10-15T11:30:00-07:00', updated_by: 'fixture' },
  { id: 2, name: 'Beta', group: 'G1', status: 'held', percent: null, detail: '', next: '', eta: '', blocker: 'waiting on review', usable: 'no', subgoals: [], updated_at: '2026-10-14T09:00:00-07:00', updated_by: 'fixture' },
  { id: 3, name: 'Gamma', group: 'G2', status: 'done', percent: 100, detail: '', next: '', eta: '', blocker: '', usable: 'yes', subgoals: [], updated_at: '2026-10-13T08:00:00-07:00', updated_by: 'fixture' },
] };
let statusHits = 0;
function api(mode, url) {
  if (url.startsWith('/api/v1/projects') || url.startsWith('/api/parent/projects')) {
    if (mode === 'error') return [500, JSON.stringify({ error: 'fixture failure' })];
    if (mode === 'malformed') return [200, '{not json'];
    if (mode === 'empty') return [200, JSON.stringify({ ...populated, count: 0, projects: [] })];
    return [200, JSON.stringify(populated)];
  }
  if (url === '/status.json') {
    statusHits++;
    if (mode === 'jobs-error') return [500, 'fixture failure'];
    if (mode === 'jobs-flake' && statusHits > 1) return [500, 'fixture failure'];
  }
  return null;
}
http.createServer(async (req, res) => {
  const url = req.url.split('?')[0];
  const a = api(MODE, url);
  if (a) { res.writeHead(a[0], { 'content-type': 'application/json' }); res.end(a[1]); return; }
  const tries = url.endsWith('/') ? [join(ROOT, url, 'index.html')] : [join(ROOT, url), join(ROOT, url, 'index.html')];
  for (const t of tries) {
    try { const b = await readFile(t); res.writeHead(200, { 'content-type': MIME[extname(t)] || 'application/octet-stream' }); res.end(b); return; } catch {}
  }
  res.writeHead(404); res.end('nf');
}).listen(4899, () => console.log('up ' + MODE));
