import { cp, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { basename, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { prerenderPosts, prerenderProjects, prerenderTopLevel } from './prerender.js';


const root = fileURLToPath(new URL('..', import.meta.url));
const publication = join(root, 'dist');
const topLevelFiles = [
  'index.html', 'engineering.html', 'product.html', 'work.html', 'resume.html',
  'contact.html', 'blog.html', 'archive.html', 'favicon.svg', 'og-image.png', 'robots.txt', 'sitemap.xml',
];
const directories = ['styles', 'scripts', 'data', 'public', 'work', 'blog'];

await rm(publication, { recursive: true, force: true });
await mkdir(publication, { recursive: true });

// Bundle CSS into 3 files before staging.
const { execFile } = await import('node:child_process');
const { promisify } = await import('node:util');
const execFileAsync = promisify(execFile);
await execFileAsync('node', [join(root, 'scripts', 'bundle-css.js')]);

// Bundle JS into a single file.
await execFileAsync('node', [join(root, 'scripts', 'bundle-js.js')]);

for (const file of topLevelFiles) {
  await cp(join(root, file), join(publication, file));
}

// Vercel's clean-URL transform reserves index.html in a staged static output.
// Keep the canonical source unchanged, but give root and SPA fallbacks a stable
// deploy-only target that is not transformed into /index.
await cp(join(root, 'index.html'), join(publication, 'root.html'));

for (const directory of directories) {
  const entries = await readdir(join(root, directory));
  const blocked = directory === 'scripts'
    ? new Set(['main.js', 'stage-publication.js', 'prerender.js', 'preview-server.js'])
    : directory === 'data'
      ? new Set()
      : new Set();
  const allowed = entries.filter((entry) => {
    if (blocked.has(entry)) return false;
    return true;
  });
  await mkdir(join(publication, directory), { recursive: true });
  await Promise.all(allowed.map((entry) => cp(
    join(root, directory, entry),
    join(publication, directory, entry),
    { recursive: true, filter: (source) => basename(source) !== '.DS_Store' },
  )));
}

await prerenderTopLevel(publication);
await prerenderProjects(publication);
await prerenderPosts(publication);

// Minify JS in dist/ — strip comments from scripts and data files.
// Runs after prerender so it doesn't affect Node-side parsing.
await execFileAsync('node', [join(root, 'scripts', 'minify-js.js')]);



// Sync to Vercel static output directory for build-output test parity.
const vercelStatic = join(root, '.vercel', 'output', 'static');
await rm(vercelStatic, { recursive: true, force: true });
await cp(publication, vercelStatic, { recursive: true });
