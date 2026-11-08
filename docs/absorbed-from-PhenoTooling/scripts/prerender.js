import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { parseHTML } from 'linkedom';
import { PROJECTS } from '../data/projects.js';
import { POSTS } from '../data/posts.js';
import { renderShell } from './components/shell.js';
import { renderHome } from './views/home.js';
import { renderWorkCatalog } from './views/work.js';
import { renderProjectDetail } from './views/project-detail.js';
import { renderResume } from './views/resume.js';
import { renderContact } from './views/contact.js';
import { renderBlogIndex } from './views/blog-index.js';
import { renderBlogPost } from './views/blog-post.js';

const TOP_LEVEL_ROUTES = [
  { file: 'index.html', route: { view: 'home' }, render: (root) => renderHome(root, { projects: PROJECTS, lens: 'engineering' }) },
  { file: 'engineering.html', route: { view: 'engineering', lens: 'engineering' }, render: (root) => renderHome(root, { projects: PROJECTS, lens: 'engineering' }) },
  { file: 'product.html', route: { view: 'product', lens: 'product' }, render: (root) => renderHome(root, { projects: PROJECTS, lens: 'product' }) },
  { file: 'work.html', route: { view: 'work' }, render: (root) => renderWorkCatalog(root, { projects: PROJECTS }) },
  { file: 'resume.html', route: { view: 'resume' }, render: (root) => renderResume(root) },
  { file: 'contact.html', route: { view: 'contact' }, render: (root) => renderContact(root) },
  { file: 'blog.html', route: { view: 'blog' }, render: (root) => renderBlogIndex(root, { posts: POSTS }) },
];

function removeInertControls(document) {
  document.querySelectorAll('button').forEach((button) => button.remove());
  document.querySelectorAll('a[href="#blog"]').forEach((link) => link.setAttribute('href', '/blog'));
  document.querySelectorAll('a[href^="#blog/"]').forEach((link) => {
    link.setAttribute('href', `/${link.getAttribute('href').slice(1)}`);
  });
}

export async function prerenderTopLevel(publication) {
  const previousDocument = globalThis.document;
  try {
    for (const { file, route, render } of TOP_LEVEL_ROUTES) {
      const { document } = parseHTML(await readFile(join(publication, file), 'utf8'));
      globalThis.document = document;
      const root = document.getElementById('view-root');
      renderShell(document.getElementById('shell-root'), { route, lens: route.lens ?? 'engineering', reader: false });
      render(root);
      removeInertControls(document);
      await writeFile(join(publication, file), document.toString());
    }
  } finally { globalThis.document = previousDocument; }
}

// Render the actual project view at build time. Browser enhancement replaces it.
export async function prerenderProjects(publication) {
  const template = await readFile(join(publication, 'work/sharecli.html'), 'utf8');
  const previousDocument = globalThis.document;
  try {
    for (const project of PROJECTS) {
      const { document } = parseHTML(template);
      globalThis.document = document;
      const root = document.getElementById('view-root');
      renderShell(document.getElementById('shell-root'), {
        route: { view: 'project', slug: project.slug },
        lens: 'engineering',
        reader: false,
      });
      renderProjectDetail(root, project.slug);
      document.title = `${project.title} — Koosha Paridehpour`;
      const url = `https://kooshapari.com/work/${project.slug}`;
      document.querySelector('link[rel="canonical"]').setAttribute('href', url);
      for (const selector of ['meta[name="description"]', 'meta[property="og:description"]']) {
        document.querySelector(selector)?.setAttribute('content', project.summary);
      }
      document.querySelector('meta[property="og:title"]')?.setAttribute('content', document.title);
      document.querySelector('meta[property="og:url"]')?.setAttribute('content', url);
      // Inert rich controls are absent from the static view; complete text and navigation stay.
      removeInertControls(document);
      await writeFile(join(publication, `work/${project.slug}.html`), document.toString());
    }
  } finally { globalThis.document = previousDocument; }
}

// Render known published posts only. Unknown blog slugs retain the SPA's existing behavior.
export async function prerenderPosts(publication) {
  const template = await readFile(join(publication, 'blog/why-we-forked-omniroute.html'), 'utf8');
  const previousDocument = globalThis.document;
  try {
    for (const post of POSTS) {
      const { document } = parseHTML(template);
      globalThis.document = document;
      const root = document.getElementById('view-root');
      renderShell(document.getElementById('shell-root'), {
        route: { view: 'post', slug: post.slug },
        lens: 'engineering',
        reader: false,
      });
      renderBlogPost(root, post.slug);
      document.title = `${post.title} — Koosha Paridehpour`;
      const url = `https://kooshapari.com/blog/${post.slug}`;
      document.querySelector('link[rel="canonical"]')?.setAttribute('href', url);
      for (const selector of ['meta[name="description"]', 'meta[property="og:description"]', 'meta[name="twitter:description"]']) {
        document.querySelector(selector)?.setAttribute('content', post.excerpt);
      }
      for (const selector of ['meta[property="og:title"]', 'meta[name="twitter:title"]']) {
        document.querySelector(selector)?.setAttribute('content', document.title);
      }
      document.querySelector('meta[property="og:url"]')?.setAttribute('content', url);
      removeInertControls(document);
      await writeFile(join(publication, `blog/${post.slug}.html`), document.toString());
    }
  } finally { globalThis.document = previousDocument; }
}
