import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, rm, copyFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { writeLegacyAliases } from '../scripts/legacy-aliases.mjs';
const script = fileURLToPath(new URL('../scripts/stage-public.mjs', import.meta.url));
test('migrated routes replace only HTML; static data and Pages Functions retain exact bytes', async () => {
  const root = await mkdtemp(join(tmpdir(), 'cockpit-routes-'));
  try {
    for (const dir of ['web/scripts', 'web/src/pages/parent', 'web/src/pages/dispensary', 'web/src/pages/economics', 'parent',
      'dispensary/data/snapshots', 'functions/api/asks', 'functions/api/display', 'functions/api/econ', 'functions/api/parent', 'functions/api/v1', 'functions/dispensary/data', 'worker', 'jobs-collector', 'collector'])
      await mkdir(join(root, dir), { recursive: true });
    await copyFile(script, join(root, 'web/scripts/stage-public.mjs'));
    const pages = ['index', 'parent/index', 'dispensary/index', 'dispensary/learned'];
    for (const page of pages) {
      await writeFile(join(root, page + '.html'), '<p>Legacy source stays unchanged</p>');
      await writeFile(join(root, 'web/src/pages', page + '.astro'), '<p>Migrated route</p>');
    }
    await writeFile(join(root, 'web/src/pages/economics/index.astro'), '<p>Economics route</p>');
    const assets: Record<string, string> = {
      'status.json': '{ "applications": [] }\n', 'dispensary/data/manifest.json': '{"dates":["2026-10-09"]}\n',
      'dispensary/data/manual.json': '[ {"price": "12.00", "extra":"unchanged"} ]\n',
      'dispensary/data/registry.json': '{ "key": {"last_seen":null} }\n',
      'dispensary/data/observations.json': '{"extra":true}\n', 'dispensary/data/status.json': '{"ok":true}\n',
      'dispensary/data/cadence.json': '{"brands":{}}\n', 'dispensary/data/deal_patterns.json': '{"stores":{}}\n',
      'dispensary/data/snapshots/2026-10-09.json': '{ "date":"2026-10-09", "stores":[] }\n',
    };
    for (const [path, value] of Object.entries(assets)) await writeFile(join(root, path), value);
    const fn = 'export function onRequest(c){return c.next();}\n';
    for (const path of ['functions/api/asks/[[path]].js', 'functions/api/display/[[path]].js', 'functions/api/econ/[[path]].js', 'functions/api/parent/[[path]].js', 'functions/api/v1/[[path]].js', 'functions/dispensary/data/[[path]].js'])
      await writeFile(join(root, path), fn);
    for (const dir of ['worker', 'jobs-collector', 'collector']) await writeFile(join(root, dir, 'keep.txt'), 'untouched');
    const result = spawnSync(process.execPath, [join(root, 'web/scripts/stage-public.mjs')], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const manifest = JSON.parse(await readFile(join(root, 'web/.staged/manifest.json'), 'utf8'));
    assert(!manifest.files.some((path: string) => path.endsWith('.html')));
    for (const [path, value] of Object.entries(assets)) {
      assert.equal(await readFile(join(root, path), 'utf8'), value);
      assert.deepEqual(await readFile(join(root, path)), await readFile(join(root, 'web/.staged/public', path)));
    }
    assert.deepEqual(manifest.functions, ['api/asks/[[path]].js', 'api/display/[[path]].js', 'api/econ/[[path]].js', 'api/parent/[[path]].js', 'api/v1/[[path]].js', 'dispensary/data/[[path]].js']);
    for (const path of manifest.functions) assert.equal(await readFile(join(root, 'web/functions', path), 'utf8'), fn);
    assert(!manifest.files.includes('economics/index.html'));
    for (const page of pages) assert.equal(await readFile(join(root, page + '.html'), 'utf8'), '<p>Legacy source stays unchanged</p>');
    for (const dir of ['worker', 'jobs-collector', 'collector']) assert.equal(await readFile(join(root, dir, 'keep.txt'), 'utf8'), 'untouched');
  } finally { await rm(root, { recursive: true, force: true }); }
});
test('learned HTML compatibility alias copies the built wrapper without overwriting assets', async () => {
  const root = await mkdtemp(join(tmpdir(), 'cockpit-alias-'));
  try {
    await mkdir(join(root, 'dispensary/learned'), { recursive: true });
    const html = '<!doctype html><a href="/dispensary/#insights">Learned patterns</a>\n';
    await writeFile(join(root, 'dispensary/learned/index.html'), html);
    await writeFile(join(root, 'dispensary/manifest.json'), '{"keep":"bytes"}\n');
    await writeLegacyAliases(root);
    assert.equal(await readFile(join(root, 'dispensary/learned.html'), 'utf8'), html);
    assert.equal(await readFile(join(root, 'dispensary/manifest.json'), 'utf8'), '{"keep":"bytes"}\n');
    await assert.rejects(writeLegacyAliases(root), { code: 'EEXIST' });
  } finally { await rm(root, { recursive: true, force: true }); }
});
test('post-build guard rejects changed JSON bytes or missing migrated routes', async () => {
  const { verifyMigratedOutput } = await import('../scripts/legacy-aliases.mjs');
  const root = await mkdtemp(join(tmpdir(), 'cockpit-build-'));
  try {
    const output = join(root, 'dist'), staged = join(root, 'staged');
    for (const dir of ['dist/parent', 'dist/dispensary/learned', 'staged/public']) await mkdir(join(root, dir), { recursive: true });
    for (const route of ['index.html', 'parent/index.html', 'dispensary/index.html', 'dispensary/learned/index.html', 'dispensary/learned.html'])
      await writeFile(join(output, route), '<!doctype html><title>Route</title>');
    await writeFile(join(staged, 'manifest.json'), '{"files":["status.json"]}');
    await writeFile(join(staged, 'public/status.json'), '{ "keep": true }\n');
    await writeFile(join(output, 'status.json'), '{ "keep": true }\n');
    await verifyMigratedOutput(output, staged);
    await writeFile(join(output, 'status.json'), '{"keep":true}\n');
    await assert.rejects(verifyMigratedOutput(output, staged), /changed data bytes/);
    await writeFile(join(output, 'status.json'), '{ "keep": true }\n');
    await rm(join(output, 'parent/index.html'));
    await assert.rejects(verifyMigratedOutput(output, staged), { code: 'ENOENT' });
  } finally { await rm(root, { recursive: true, force: true }); }
});
