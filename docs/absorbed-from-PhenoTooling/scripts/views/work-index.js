import { PROJECTS } from '../../data/projects.js';
import { el } from '../components/dom.js';

const FILTERS = [
  ['all', 'All work'],
  ['engineering', 'Engineering'],
  ['product', 'Product'],
  ['systems', 'Systems'],
  ['ai-ml', 'AI/ML'],
  ['developer-tools', 'Developer Tools'],
  ['cloud', 'Cloud'],
  ['physical-product', 'Physical Product'],
  ['historical', 'Historical'],
];

function matches(project, filter) {
  if (filter === 'all') return true;
  if (filter === 'historical') return project.status === 'historical';
  if (filter === 'engineering' || filter === 'product') return project.lens?.includes(filter);
  if (filter === 'ai-ml') return project.category === 'ai-ml' || project.category === 'ai-infrastructure';
  return project.category === filter;
}

function card(project) {
  return el('article', { class: 'project-card' },
    project.gallery?.[0] ? el('img', { class: 'project-card-image', src: project.gallery[0], alt: project.title + ' project image', loading: 'lazy', width: '1200', height: '700' }) : null,
    el('div', { class: 'project-card-top' },
      el('span', { class: 'eyebrow' }, project.category),
      el('span', { class: 'status-pill' }, project.status),
    ),
    el('h2', {}, el('a', { href: '#work/' + project.slug, class: 'card-title-link' }, project.title)),
    el('p', {}, project.summary),
    project.technologies?.length ? el('div', { class: 'tag-row' }, project.technologies.map(t => el('span', { class: 'tag' }, t))) : null,
    project.repo ? el('a', { href: project.repo, target: '_blank', rel: 'noreferrer', class: 'text-link' }, 'View repository') : null,
  );
}

export function renderWorkIndex(root, { projects = PROJECTS } = {}) {
  const grid = el('div', { class: 'project-grid', 'aria-live': 'polite' });
  const count = el('span', { class: 'work-filter-count', 'aria-live': 'polite' });

  const buttons = FILTERS.map(([value, label], index) =>
    el('button', {
      type: 'button', class: 'work-filter', 'data-filter': value,
      'aria-pressed': index === 0 ? 'true' : 'false',
      onclick: () => {
        const filtered = projects.filter(p => matches(p, value));
        grid.replaceChildren(...filtered.map(card));
        count.textContent = filtered.length + ' ' + (filtered.length === 1 ? 'project' : 'projects');
        buttons.forEach(b => b.setAttribute('aria-pressed', b === buttons[index] ? 'true' : 'false'));
      },
    }, label),
  );

  const all = projects.filter(p => matches(p, 'all'));
  grid.append(...all.map(card));
  count.textContent = all.length + ' projects';

  root.replaceChildren(
    el('section', { class: 'view active portfolio-view' },
      el('p', { class: 'eyebrow' }, 'WORK'),
      el('h1', {}, 'Work'),
      el('p', { class: 'lede' }, 'Curated projects across engineering, product, systems, AI/ML, cloud, and historical work.'),
      el('div', { class: 'work-filter-bar' },
        el('div', { class: 'work-filter-heading' },
          el('span', { class: 'section-sub' }, 'Filter by focus'), count,
        ),
        el('div', { class: 'work-filters', role: 'group', 'aria-label': 'Filter work by focus' }, buttons),
      ),
      grid,
    ),
  );
}

