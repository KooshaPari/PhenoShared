import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, copyFile, writeFile, readFile, symlink, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const script = fileURLToPath(new URL('../scripts/stage-public.mjs', import.meta.url));
async function fixture() {
  const root = await mkdtemp(join(tmpdir(), 'cockpit-stage-'));
  for (const dir of ['web/scripts', 'web/src/pages/economics', 'parent', 'dispensary/data/snapshots', 'functions/api/asks', 'functions/api/display', 'functions/api/econ', 'functions/api/parent', 'functions/api/v1', 'functions/dispensary/data', 'worker']) await mkdir(join(root, dir), { recursive: true });
  await copyFile(script, join(root, 'web/scripts/stage-public.mjs'));
  for (const path of ['index.html', 'parent/index.html', 'dispensary/index.html']) await writeFile(join(root, path), '<!doctype html><title>Legacy</title>');
  await writeFile(join(root, 'web/src/pages/economics/index.astro'), '<p>Economics</p>');
  await writeFile(join(root, 'status.json'), '{ "applications": [] }\n');
  await writeFile(join(root, 'dispensary/data/manifest.json'), '{"dates":[]}\n');
  const fn = 'export function onRequest(c){ return c.next(); }\n';
  for (const path of ['functions/api/asks/[[path]].js', 'functions/api/display/[[path]].js', 'functions/api/econ/[[path]].js', 'functions/api/parent/[[path]].js', 'functions/api/v1/[[path]].js', 'functions/dispensary/data/[[path]].js']) await writeFile(join(root, path), fn);
  await writeFile(join(root, 'worker/keep.txt'), 'unchanged');
  return root;
}
const run = (root: string) => spawnSync(process.execPath, [join(root, 'web/scripts/stage-public.mjs')], { encoding: 'utf8' });
test('staging preserves bytes and isolates collector source', async () => {
  const root = await fixture();
  try {
    assert.equal(run(root).status, 0);
    assert.deepEqual(await readFile(join(root, 'status.json')), await readFile(join(root, 'web/.staged/public/status.json')));
    assert.deepEqual(await readFile(join(root, 'functions/dispensary/data/[[path]].js')), await readFile(join(root, 'web/functions/dispensary/data/[[path]].js')));
    assert.equal(await readFile(join(root, 'worker/keep.txt'), 'utf8'), 'unchanged');
    const manifest = JSON.parse(await readFile(join(root, 'web/.staged/manifest.json'), 'utf8'));
    assert.deepEqual(manifest.functions, ['api/asks/[[path]].js', 'api/display/[[path]].js', 'api/econ/[[path]].js', 'api/parent/[[path]].js', 'api/v1/[[path]].js', 'dispensary/data/[[path]].js']);
    assert(!manifest.files.some((p: string) => p.startsWith('worker/')));
    assert(!manifest.files.includes('economics/index.html'));
    await symlink(join(root, 'worker/keep.txt'), join(root, 'dispensary/data/manual.json'));
    assert.notEqual(run(root).status, 0);
    assert.deepEqual(await readFile(join(root, 'status.json')), await readFile(join(root, 'web/.staged/public/status.json')));
  } finally { await rm(root, { recursive: true, force: true }); }
});
test('public duplicate paths and generated route collisions fail', async () => {
  const root = await fixture();
  try {
    await mkdir(join(root, 'web/public/parent'), { recursive: true });
    await writeFile(join(root, 'web/public/parent/index.html'), 'shadow');
    assert.notEqual(run(root).status, 0);
    await rm(join(root, 'web/public'), { recursive: true });
    await mkdir(join(root, 'web/src/pages/dispensary/learned'), { recursive: true });
    await writeFile(join(root, 'web/src/pages/dispensary/learned/index.astro'), '<p>New</p>');
    await writeFile(join(root, 'dispensary/learned.html'), '<p>Old</p>');
    assert.notEqual(run(root).status, 0);
  } finally { await rm(root, { recursive: true, force: true }); }
});
