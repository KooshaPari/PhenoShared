import { filterWorkProjects } from '../work-filters.js';
import { WORK_FILTERS } from '../work-filters.js';
import { el } from '../components/dom.js';

export const CATALOG_GROUPS = [
  { kind: 'featured', label: 'Featured work', presentation: 'featured' },
  { kind: 'compact', label: 'Selected work', presentation: 'specimen-sheet' },
  { kind: 'archive', label: 'Archive', presentation: 'chronological-drawer' },
];

export function classifyCatalogProject(project) {
  if (project.featured) return 'featured';
  if (project.status === 'historical') return 'archive';
  return 'compact';
}

function archiveTimestamp(project) {
  const value = project.archiveDate ?? project.date ?? project.year;
  if (value == null) return null;

  const timestamp = Date.parse(String(value));
  return Number.isNaN(timestamp) ? null : timestamp;
}

function chronologicalArchive(projects) {
  return projects
    .map((project, sourceIndex) => ({ project, sourceIndex, timestamp: archiveTimestamp(project) }))
    .sort((left, right) => {
      if (left.timestamp == null && right.timestamp == null) return left.sourceIndex - right.sourceIndex;
      if (left.timestamp == null) return 1;
      if (right.timestamp == null) return -1;
      return right.timestamp - left.timestamp || left.sourceIndex - right.sourceIndex;
    })
    .map(({ project }) => project);
}

// Pure catalog view-model. The integration lane owns DOM rendering, controls, and CSS.
export function buildWorkCatalog(projects, filter = 'all') {
  const groupsByKind = new Map(CATALOG_GROUPS.map(({ kind }) => [kind, []]));
  const filtered = filterWorkProjects(projects, filter);

  for (const project of filtered) {
    groupsByKind.get(classifyCatalogProject(project)).push(project);
  }

  return {
    filter,
    total: filtered.length,
    groups: CATALOG_GROUPS.map((group) => ({
      ...group,
      projects: group.kind === 'archive'
        ? chronologicalArchive(groupsByKind.get(group.kind))
        : groupsByKind.get(group.kind),
    })),
  };
}

function projectLink(project) {
  return el('a', { href: `/work/${encodeURIComponent(project.slug)}`, class: 'work-catalog__project-link' }, project.title);
}

function projectMeta(project) {
  return el('p', { class: 'work-catalog__meta' }, `${project.category} / ${project.status}`);
}

const FAMILY_MAP = {
  netweave: 'netweave',
  sharecli: 'sharecli',
  omniroute: 'omniroute',
  'gmk-arch': 'physical',
  witf: 'physical',
  'dss-cipher': 'physical',
  substrate: 'substrate',
  'phenotype-omlx': 'omlx',
};

const CARD_IMAGES = {
  netweave: { src: '/public/projects/netweave/desktop-01-v3.webp', alt: 'NetWeave traffic simulation showing directed-graph routing and cellular automata lane behavior across a road network.' },
  'gmk-arch': { src: '/public/projects/gmk-arch/hero.png', alt: 'Transparent GMK Arch wordmark with a pale ARCH letterform and teal Arch Linux and GMK marks.' },
  witf: { src: '/public/projects/witf/hero-01.webp', alt: 'Black WITF Board keyboard shown from above on a warm concrete-colored surface, revealing its split Alice layout.' },
  sharecli: { src: '/public/projects/sharecli/card.webp', alt: 'ShareCLI runtime and resource observation interface for coding-agent concurrency.' },
  omniroute: { src: '/public/projects/omniroute/card.webp', alt: 'OmniRoute policy-aware multi-provider routing topology.' },
  substrate: { src: '/public/projects/substrate/card.webp', alt: 'Substrate AI execution and provider-routing boundary.' },
  'phenotype-omlx': { src: '/public/projects/phenotype-omlx/card.webp', alt: 'phenotype-omlx MLX inference research stack with Rust performance cores.' },
};

function featuredProject(project) {
  const family = FAMILY_MAP[project.slug];
  const image = CARD_IMAGES[project.slug];
  const href = `/work/${encodeURIComponent(project.slug)}`;
  const attrs = {
    class: 'work-catalog__featured-project',
    href,
    'aria-label': `${project.title}, ${project.category}, ${project.status}`,
  };
  if (family) {
    attrs['data-family'] = family;
    attrs.style = `--family-accent: var(--family-${family}-active, var(--family-${family}))`;
  }

  const children = [
    el('p', { class: 'work-catalog__featured-status' }, `${project.category} / ${project.status}`),
  ];

  if (image) {
    children.push(
      el('div', { class: 'work-catalog__featured-image' },
        el('img', { src: image.src, alt: image.alt, loading: 'lazy', decoding: 'async' }),
      ),
    );
  }

  children.push(
    el('h3', {}, project.title),
    el('p', { class: 'work-catalog__featured-summary' }, project.summary),
  );

  if (project.technologies?.length) {
    children.push(
      el('div', { class: 'work-catalog__featured-tech' },
        project.technologies.slice(0, 5).map((t) => el('span', {}, t)),
      ),
    );
  }

  return el('a', attrs, ...children);
}

function compactProject(project) {
  const family = FAMILY_MAP[project.slug];
  const attrs = { class: 'work-catalog__specimen', 'data-reveal': 'up' };
  if (family) {
    attrs['data-family'] = family;
    attrs.style = `--family-accent: var(--family-${family}-active, var(--family-${family}))`;
  }

  return el(
    'li',
    attrs,
    el('p', { class: 'work-catalog__specimen-code' }, project.slug),
    el('h3', {}, projectLink(project)),
    projectMeta(project),
    el('p', { class: 'work-catalog__summary' }, project.summary),
  );
}

function archiveProject(project) {
  return el(
    'li',
    { class: 'work-catalog__archive-item' },
    el('span', { class: 'work-catalog__archive-mark', 'aria-hidden': 'true' }, '---'),
    el('div', {}, el('h3', {}, projectLink(project)), projectMeta(project)),
  );
}

function renderGroup(group) {
  if (group.projects.length === 0) return null;

  if (group.kind === 'archive') {
    return el(
      'details',
      { class: 'work-catalog__group work-catalog__group--archive', 'data-presentation': group.presentation },
      el('summary', {}, `${group.label} (${group.projects.length})`),
      el('ol', { class: 'work-catalog__archive-list' }, group.projects.map(archiveProject)),
    );
  }

  const projects = group.kind === 'featured'
    ? el('div', { class: 'work-catalog__featured-list' }, group.projects.map(featuredProject))
    : el('ol', { class: 'work-catalog__specimen-list' }, group.projects.map(compactProject));

  return el(
    'section',
    { class: `work-catalog__group work-catalog__group--${group.kind}`, 'data-presentation': group.presentation },
    el('h2', {}, group.label),
    projects,
  );
}

export function renderWorkCatalog(root, { projects }) {
  const render = (filter = 'all', focusFilter = null) => {
    const catalog = buildWorkCatalog(projects, filter);
    const count = el(
      'p',
      { class: 'work-catalog__count', 'aria-live': 'polite' },
      `${catalog.total} ${catalog.total === 1 ? 'project' : 'projects'}`,
    );
    const controls = WORK_FILTERS.map(([value, label]) => el(
      'button',
      {
        type: 'button',
        class: 'work-catalog__filter',
        'data-filter': value,
        'aria-pressed': String(catalog.filter === value),
        onclick: () => render(value, value),
      },
      label,
    ));

    root.replaceChildren(
      el(
        'section',
        { class: 'view active portfolio-view work-catalog' },
        el('p', { class: 'eyebrow' }, 'WORK'),
        el('h1', {}, 'Work'),
        el('p', { class: 'lede' }, 'Curated systems, products, experiments, and historical work.'),
        el(
          'div',
          { class: 'work-catalog__controls' },
          el('div', { class: 'work-catalog__control-heading' }, el('span', {}, 'Filter by focus'), count),
          el('div', { role: 'group', 'aria-label': 'Filter work by focus', class: 'work-catalog__filters' }, controls),
        ),
        catalog.groups.map(renderGroup),
      ),
    );

    if (focusFilter) {
      controls.find((control) => control.getAttribute('data-filter') === focusFilter)?.focus();
    }
  };

  render();
}
