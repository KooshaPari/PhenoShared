import { POSTS } from '../../data/posts.js';
import { el } from '../components/dom.js';

function postCard(post) {
  const tags = post.tags?.length
    ? el('div', { class: 'post-card-tags' },
        post.tags.map((t) => el('span', { class: 'tag' }, t)))
    : null;

  return el('article', { class: 'post-card' },
    el('div', { class: 'post-card-top' },
      el('span', { class: 'eyebrow' }, post.provenance ?? 'Writing'),
      el('span', { class: 'post-card-meta' },
        el('time', { datetime: post.date }, post.date),
        el('span', { 'aria-hidden': 'true' }, '·'),
        el('span', {}, post.readingTime ?? ''),
      ),
    ),
    el('h2', {}, el('a', { href: '/blog/' + post.slug, class: 'card-title-link' }, post.title)),
    el('p', { class: 'post-card-excerpt' }, post.excerpt),
    tags,
  );
}

export function renderBlogIndex(root, { posts = POSTS } = {}) {
  root.replaceChildren(
    el('section', { class: 'view active blog-view' },
      el('p', { class: 'eyebrow' }, 'WRITING'),
      el('h1', {}, 'Writing'),
      el('p', { class: 'lede' },
        'Notes on the work — systems, OSS contributions, fork discipline, and the long arc of building infra that has to keep running.'
      ),
      el('div', { class: 'post-list' },
        posts.map(postCard),
      ),
    ),
  );
}
