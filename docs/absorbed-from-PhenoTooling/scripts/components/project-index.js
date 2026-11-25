import { el } from './dom.js';

const GROUPS = [
  ['Featured', (project) => project.featured],
  ['Systems', (project) => project.category === 'systems'],
  ['AI / ML', (project) => ['ai-ml', 'ai-infrastructure'].includes(project.category)],
  ['Physical Products', (project) => project.category === 'physical-product'],
  ['Research', (project) => project.status === 'research' || project.category === 'simulation'],
  ['Archive', (project) => project.status === 'historical'],
  ['Compact', () => true],
];

function partitionProjects(projects) {
  const claimed = new Set();

  return GROUPS.map(([label, matches]) => {
    const entries = projects.filter((project) => {
      if (claimed.has(project.slug) || !matches(project)) return false;
      claimed.add(project.slug);
      return true;
    });
    return [label, entries];
  }).filter(([, entries]) => entries.length > 0);
}

export function createProjectIndex({ projects, onNavigate = () => {} }) {
  let returnFocus = null;
  const titleId = 'project-index-title';
  const dialog = el('dialog', {
    class: 'project-index',
    'aria-labelledby': titleId,
  });

  function close() {
    if (!dialog.open) return;
    dialog.close();
  }

  function render() {
    const groups = partitionProjects(projects);
    const closeButton = el(
      'button',
      { class: 'project-index-close', type: 'button', onclick: close },
      'Close',
    );

    dialog.replaceChildren(
      el(
        'div',
        { class: 'project-index-head' },
        el('div', {}, el('p', { class: 'atelier-label' }, 'Complete catalog'), el('h2', { id: titleId }, 'Project Index')),
        closeButton,
      ),
      el(
        'div',
        { class: 'project-index-groups' },
        groups.map(([label, entries], groupIndex) =>
          el(
            'section',
            { class: 'project-index-group', 'aria-labelledby': `index-group-${groupIndex}` },
            el('h3', { id: `index-group-${groupIndex}` }, label),
            el(
              'ol',
              {},
              entries.map((project, index) =>
                el(
                  'li',
                  {},
                  el(
                    'a',
                    {
                      href: `/work/${project.slug}`,
                      onclick: () => {
                        onNavigate(project);
                        close();
                      },
                    },
                    el('span', { class: 'project-index-number' }, String(index + 1).padStart(2, '0')),
                    el('strong', {}, project.title),
                    el('span', {}, project.summary),
                    el('small', {}, `${project.category} / ${project.status}`),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  function open(trigger = document.activeElement) {
    returnFocus = trigger instanceof HTMLElement ? trigger : null;
    render();
    if (!dialog.open) dialog.showModal();
    dialog.querySelector('a, button')?.focus();
  }

  dialog.addEventListener('cancel', (event) => {
    event.preventDefault();
    close();
  });
  dialog.addEventListener('close', () => {
    returnFocus?.focus();
    returnFocus = null;
  });

  render();
  return { element: dialog, open, close, render };
}
