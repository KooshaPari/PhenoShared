import { copyFile, lstat, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const repo = resolve(web, '..');
const staged = join(web, '.staged'), publicOut = join(staged, 'public');
const functionPath = 'dispensary/data/[[path]].js';
const functionPaths = ['api/answers/[[path]].js', 'api/asks/[[path]].js', 'api/display/[[path]].js', 'api/econ/[[path]].js', 'api/ledger/[[path]].js', 'api/parent/[[path]].js', 'api/v1/[[path]].js', functionPath, 'lib/http.js', 'lib/routes/answers.js', 'lib/routes/asks.js', 'lib/routes/display.js', 'lib/routes/econ.js', 'lib/routes/ledger.js', 'lib/routes/parent.js', 'lib/routes/v1.js']; // sorted; answers + econ + ledger + cockpit-api + dispensary + shared lib + route modules
const plans = [], destinations = new Set();
async function statOrNull(path) {
  try { return await lstat(path); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}
async function safePath(base, path) {
  const target = resolve(base, path), rel = relative(base, target);
  if (rel.startsWith(`..${sep}`) || rel === '..' || !rel) throw new Error(`Invalid path: ${path}`);
  let cursor = base;
  for (const part of rel.split(sep)) {
    cursor = join(cursor, part);
    if ((await statOrNull(cursor))?.isSymbolicLink()) throw new Error(`Symlink not allowed: ${cursor}`);
  }
  return target;
}
async function add(source, destination, required = false) {
  const src = await safePath(repo, source), stat = await statOrNull(src);
  if (!stat) { if (required) throw new Error(`Required public source missing: ${source}`); return; }
  if (!stat.isFile()) throw new Error(`Expected regular file: ${source}`);
  if (destinations.has(destination)) throw new Error(`Output collision: ${destination}`);
  if (source.endsWith('.json')) JSON.parse(await readFile(src, 'utf8'));
  await safePath(publicOut, destination);
  destinations.add(destination); plans.push({ src, destination });
}
async function page(source, destination, astroSource, required = true) {
  if (await statOrNull(await safePath(web, astroSource))) return;
  await add(source, destination, required);
}
async function walk(base, prefix = '') {
  const dir = prefix ? await safePath(base, prefix) : base, stat = await statOrNull(dir);
  if (!stat) return [];
  if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error(`Unsafe directory: ${dir}`);
  const files = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isSymbolicLink()) throw new Error(`Symlink not allowed: ${path}`);
    if (entry.isDirectory()) files.push(...await walk(base, path));
    else if (entry.isFile()) files.push(path);
    else throw new Error(`Unsupported file: ${path}`);
  }
  return files.sort();
}
// Validate all inputs before replacing generated output. Never traverse worker/.
await page('index.html', 'index.html', 'src/pages/index.astro');
await page('parent/index.html', 'parent/index.html', 'src/pages/parent/index.astro');
await page('dispensary/index.html', 'dispensary/index.html', 'src/pages/dispensary/index.astro');
await page('economics/index.html', 'economics/index.html', 'src/pages/economics/index.astro');
await page('status/index.html', 'status/index.html', 'src/pages/status/index.astro');
await page('dispensary/learned.html', 'dispensary/learned.html', 'src/pages/dispensary/learned.astro', false);
await add('status.json', 'status.json', true);
for (const name of ['manifest', 'manual', 'registry', 'observations', 'status', 'cadence', 'deal_patterns']) {
  await add(`dispensary/data/${name}.json`, `dispensary/data/${name}.json`, name === 'manifest');
}
const snapshots = await safePath(repo, 'dispensary/data/snapshots');
for (const file of await walk(snapshots)) {
  if (!/^\d{4}-\d{2}-\d{2}\.json$/.test(file)) throw new Error(`Unexpected snapshot asset: ${file}`);
  await add(`dispensary/data/snapshots/${file}`, `dispensary/data/snapshots/${file}`);
}
// This directory is intentionally public; reject hidden files and server artifacts.
for (const file of await walk(join(web, 'public'))) {
  if (file.split('/').some(part => part.startsWith('.')) ||
      (!/\.(css|js|mjs|svg|png|jpe?g|webp|ico|woff2?|txt|json|html)$/.test(file) &&
       !['_headers', '_redirects'].includes(file)) || file === '_worker.js') {
    throw new Error(`Unexpected web/public asset: ${file}`);
  }
  await add(`web/public/${file}`, file);
}
const rootFunctions = await safePath(repo, 'functions'), functionFiles = await walk(rootFunctions);
if (functionFiles.length !== functionPaths.length || functionFiles.some((f, i) => f !== functionPaths[i])) {
  throw new Error('Pages Functions changed: review the explicit staging allowlist.');
}
for (const file of await walk(join(web, 'functions'))) {
  if (!functionPaths.includes(file)) throw new Error(`Unexpected generated Pages Function: ${file}`);
}
const functionCopies = [];
for (const fp of functionPaths) functionCopies.push([await safePath(rootFunctions, fp), await safePath(web, `functions/${fp}`)]);
await safePath(web, '.staged/public');
for (const output of destinations) {
  if (!output.endsWith('.html')) continue;
  const route = output === 'index.html' ? 'index' : output.endsWith('/index.html') ? output.slice(0, -11) : output.slice(0, -5);
  for (const extension of ['astro', 'tsx', 'md', 'mdx']) {
    if (await statOrNull(join(web, 'src/pages', `${route}.${extension}`)) || await statOrNull(join(web, 'src/pages', route, `index.${extension}`))) {
      throw new Error(`Public asset shadows generated route: ${output}`);
    }
  }
}
await rm(staged, { recursive: true, force: true });
await mkdir(publicOut, { recursive: true });
for (const { src, destination } of plans) {
  const dest = join(publicOut, destination);
  await mkdir(dirname(dest), { recursive: true }); await copyFile(src, dest);
}
for (const [from, to] of functionCopies) {
  await mkdir(dirname(to), { recursive: true });
  await copyFile(from, to);
}
await writeFile(join(staged, 'manifest.json'), JSON.stringify({
  files: plans.map(p => p.destination), function: functionPath, functions: functionPaths,
}, null, 2) + '\n');
console.log(`Staged ${plans.length} public files and the Pages Functions (dispensary DISP + cockpit-api).`);
