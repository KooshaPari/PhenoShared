import { createArtifact, physicalPlate } from '../components/artifact.js';
import { el } from '../components/dom.js';
import { IDENTITY, PERSONAS } from '../../data/phenotype.js';

const LENS_PRIORITY = {
  engineering: ['witf', 'sharecli', 'substrate', 'phenotype-omlx', 'netweave', 'gmk-arch'],
  product: ['witf', 'gmk-arch', 'sharecli', 'substrate', 'phenotype-omlx', 'netweave'],
};

export function orderFeaturedProjects(projects, lens) {
  const priority = LENS_PRIORITY[lens] ?? LENS_PRIORITY.engineering;
  const order = new Map(priority.map((slug, index) => [slug, index]));

  return projects
    .filter((project) => project.featured && project.presentation)
    .toSorted((a, b) => (order.get(a.slug) ?? priority.length) - (order.get(b.slug) ?? priority.length));
}

function identityBlock(lens) {
  if (lens === 'engineering') return engineeringIntro();
  if (lens === 'product') return productIntro();

  // Default: combined atelier intro (homepage)
  return el(
    'div',
    { class: 'home-identity' },
    el('p', { class: 'atelier-label' }, `${IDENTITY.legalName} / Technical Atelier`),
    el('h1', {}, 'I build software systems and technical products \u2014 from distributed routing infrastructure to physical hardware launches.'),
    el('p', { class: 'home-intro' }, 'This is where I show the work.'),
    el('p', { class: 'home-reading', 'aria-live': 'polite' }, 'Engineering lens: architecture, runtime constraints, interfaces, and verification.'),
    el(
      'nav',
      { class: 'home-primary-links', 'aria-label': 'Portfolio readings' },
      el('a', { href: '/engineering' }, 'Read Engineering'),
      el('a', { href: '/product' }, 'Read Product'),
    ),
    el('p', { class: 'home-contact' },
      el('a', { href: `mailto:${IDENTITY.email}` }, IDENTITY.email),
    ),
  );
}

function engineeringIntro() {
  const domains = [
    { name: 'Systems & Runtime', desc: 'OS-adjacent runtimes, process management, FUSE, Tokio async runtimes' },
    { name: 'Distributed Backends', desc: 'Provider routing, circuit breakers, SSE streaming, budget enforcement' },
    { name: 'AI / Agent Infrastructure', desc: 'Multi-provider dispatch, agent orchestration, MCP tooling, observability' },
    { name: 'Performance & Tooling', desc: 'Rust performance cores, speculative decoding, evaluation harnesses' },
  ];

  return el(
    'div',
    { class: 'home-identity home-identity--engineering' },
    el('p', { class: 'atelier-label' }, `${IDENTITY.legalName} / Engineering`),
    el('h1', {}, 'OS-adjacent runtimes, agent infrastructure, distributed backends, and compiler-/kernel-aware engineering.'),
    el('p', { class: 'home-intro' },
      'I work at the systems boundary \u2014 where process management, provider routing, and runtime constraints shape what software can actually do.',
    ),
    el('div', { class: 'engineering-domains', 'data-reveal': 'up', 'data-reveal-delay': '200' },
      el('p', { class: 'engineering-domains__label' }, 'Technical domains'),
      ...domains.map((d, i) => el('div', { class: 'engineering-domain', 'data-reveal': 'scale', 'data-reveal-delay': String(300 + i * 80) },
        el('h3', { class: 'engineering-domain__name' }, d.name),
        el('p', { class: 'engineering-domain__desc' }, d.desc),
      )),
    ),
    el(
      'nav',
      { class: 'home-primary-links', 'aria-label': 'Navigate' },
      el('a', { href: '/product' }, 'Read Product'),
      el('a', { href: '/resume' }, 'View Resume'),
    ),
  );
}

function productIntro() {
  return el(
    'div',
    { class: 'home-identity home-identity--product' },
    el('p', { class: 'atelier-label' }, `${IDENTITY.legalName} / Product`),
    el('h1', {}, 'Leads cross-functional execution, ships commercial outcomes, owns product economics end-to-end.'),
    el('p', { class: 'home-intro' },
      'I lead cross-functional execution from ambiguous initiative to working product. My work spans hardware launches, international distribution, and AI product strategy.',
    ),
    el(
      'nav',
      { class: 'home-primary-links', 'aria-label': 'Navigate' },
      el('a', { href: '/engineering' }, 'Read Engineering'),
      el('a', { href: '/resume' }, 'View Resume'),
    ),
  );
}

export function renderHome(root, { projects, lens = 'engineering' }) {
  const featured = orderFeaturedProjects(projects, lens);
  const [witf, ...sequence] = featured;
  const titleId = 'home-featured-title';

  if (!witf) {
    const empty = el(
      'section',
      { class: 'home-empty' },
      el('h1', {}, 'Technical Atelier'),
      el('p', {}, 'Featured project records are unavailable.'),
    );
    root.replaceChildren(empty);
    return empty;
  }

  const openingArtifact = physicalPlate(witf, lens);
  openingArtifact.classList.add('home-opening-artifact');

  const view = el(
    'div',
    { class: `home-view home-view--${lens}`, 'data-lens': lens },
    el(
      'section',
      { class: 'home-opening', 'aria-label': 'Technical Atelier introduction and WITF artifact' },
      identityBlock(lens),
      openingArtifact,
    ),
    el(
      'section',
      { class: 'home-featured', 'aria-labelledby': titleId },
      el(
        'header',
        { class: 'home-featured-heading', 'data-reveal': 'fade', 'data-reveal-delay': '100' },
        el('p', { class: 'atelier-label' }, lens === 'engineering' ? 'engineering studies' : lens === 'product' ? 'product studies' : `${lens} lens / selected studies`),
        el('h2', { id: titleId }, lens === 'engineering' ? 'Engineering projects' : lens === 'product' ? 'Product projects' : 'Selected projects'),
        el('p', {}, lens === 'engineering' ? 'Systems, runtimes, and infrastructure \u2014 ordered by technical depth.' : lens === 'product' ? 'Hardware launches, distribution, and outcomes \u2014 ordered by commercial impact.' : 'Same work, reordered by the decisions each lens brings forward.'),
      ),
      el(
        'div',
        { class: 'home-artifact-sequence' },
        sequence.map((record, index) => {
          const artifact = createArtifact(record, lens);
          artifact.style.setProperty('--artifact-order', index);
          return artifact;
        }),
      ),
    ),
  );

  root.replaceChildren(view);
  return view;
}
