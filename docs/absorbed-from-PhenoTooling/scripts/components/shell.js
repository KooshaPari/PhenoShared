import { el } from './dom.js';
import { initDarkMode } from '../dark-mode.js';

const ROUTES = [
  ['/work', 'Work'],
  ['/blog', 'Writing'],
  ['/resume', 'Resume'],
  ['/contact', 'Contact'],
];

export function renderShell(
  root,
  { route, lens, reader, onLensChange = () => {}, onReaderToggle = () => {}, onIndexOpen = () => {}, states = {} },
) {
  const currentView = route?.view === 'project' ? 'work'
    : route?.view === 'post' ? 'blog'
    : route?.view;

  const navigation = el(
    'nav',
    {
      class: 'atelier-nav',
      'aria-label': 'Primary navigation',
      'data-state': states.nav || 'idle',
    },
    ROUTES.map(([href, label]) =>
      el(
        'a',
        {
          href,
          ...(currentView === label.toLowerCase() ? { 'aria-current': 'page' } : {}),
        },
        label,
      ),
    ),
  );

  const lensControl = el(
    'div',
    {
      class: 'lens-control',
      role: 'group',
      'aria-label': 'Portfolio lens',
      'data-state': states.lens || 'idle',
    },
    ['engineering', 'product'].map((value) =>
      el(
        'button',
        {
          type: 'button',
          'aria-pressed': String(lens === value),
          'data-state': states[`lens-${value}`] || 'idle',
          onclick: () => onLensChange(value),
        },
        value === 'engineering' ? 'Engineering' : 'Product',
      ),
    ),
  );

  const readerControl = el(
    'button',
    {
      id: 'reader-toggle',
      class: 'reader-toggle index-trigger',
      type: 'button',
      'aria-pressed': String(reader),
      'data-state': states.reader || (reader ? 'active' : 'pending'),
      onclick: onReaderToggle,
      title: reader ? 'Exit Reader Mode' : 'Enter Reader Mode (R)',
    },
    reader ? 'Exit Reader' : 'Reader',
  );

  const header = el(
    'header',
    {
      class: 'atelier-header',
      'data-state': states.header || 'idle',
    },
    el(
      'a',
      { class: 'atelier-identity', href: '/' },
      el('strong', {}, 'Koosha Paridehpour'),
      el('span', {}, 'Systems / products / infrastructure'),
    ),
    navigation,
    el(
      'div',
      { class: 'atelier-tools' },
      lensControl,
      readerControl,
      el(
        'button',
        { class: 'index-trigger', type: 'button', onclick: onIndexOpen },
        'Index',
      ),
    ),
  );

  const footer = el(
    'footer',
    { class: 'footer' },
    el('span', {}, 'Koosha Paridehpour · kooshapari.com'),
    el('span', {}, 'Koosha Paridehpour — Systems engineer, product builder, keyboard enthusiast.'),
  );

  const appRoot = document.getElementById('app');
  appRoot.replaceChildren(header, document.getElementById('view-root'), footer);

  // Insert dark mode toggle into .atelier-tools each time shell is rendered.
  // renderShell uses replaceChildren which destroys prior DOM, so the toggle
  // must be re-inserted on every navigation.
  initDarkMode({ toolbar: header.querySelector('.atelier-tools') });

  return header;
}
