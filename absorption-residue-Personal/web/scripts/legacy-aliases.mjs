import { copyFile, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
export async function writeLegacyAliases(directory) {
  // Same shared-layout compatibility page at both old spellings.
  // Never overwrite a staged file or change a data asset.
  await copyFile(join(directory, 'dispensary/learned/index.html'),
    join(directory, 'dispensary/learned.html'), constants.COPYFILE_EXCL);
}
export async function verifyMigratedOutput(directory, stagedDirectory) {
  for (const route of ['index.html', 'parent/index.html', 'dispensary/index.html',
    'dispensary/learned/index.html', 'dispensary/learned.html']) {
    const html = await readFile(join(directory, route), 'utf8');
    if (!html.toLowerCase().includes('<!doctype html>')) throw new Error('Missing HTML route: ' + route);
  }
  const manifest = JSON.parse(await readFile(join(stagedDirectory, 'manifest.json'), 'utf8'));
  for (const asset of manifest.files) {
    if (!asset.endsWith('.json')) continue;
    if (asset.split('/').some(part => !part || part === '.' || part === '..') || asset.startsWith('/') || asset.includes('\\'))
      throw new Error('Invalid staged data path');
    const source = await readFile(join(stagedDirectory, 'public', asset));
    const built = await readFile(join(directory, asset));
    if (!source.equals(built)) throw new Error('Build changed data bytes: ' + asset);
  }
}
export default function legacyAliases() {
  return { name: 'cockpit-legacy-aliases', hooks: {
    'astro:build:done': async ({ dir }) => {
      const directory = fileURLToPath(dir);
      await writeLegacyAliases(directory);
      await verifyMigratedOutput(directory, fileURLToPath(new URL('../.staged/', import.meta.url)));
    },
  } };
}
