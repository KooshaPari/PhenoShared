export const WORK_FILTERS = [
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

const FILTER_VALUES = new Set(WORK_FILTERS.map(([value]) => value));

export function matchesWorkFilter(project, filter) {
  if (!FILTER_VALUES.has(filter)) return false;
  if (filter === 'all') return true;
  if (filter === 'historical') return project.status === 'historical';
  if (filter === 'engineering' || filter === 'product') {
    return project.lens?.includes(filter) ?? false;
  }
  if (filter === 'ai-ml') {
    return project.category === 'ai-ml' || project.category === 'ai-infrastructure';
  }
  return project.category === filter;
}

export function filterWorkProjects(projects, filter) {
  return projects.filter((project) => matchesWorkFilter(project, filter));
}
