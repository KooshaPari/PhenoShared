import { POSTS } from '../../data/posts.js';
import { el } from '../components/dom.js';

function renderBlock(block) {
  switch (block.type) {
    case 'heading': {
      const level = block.level ?? 2;
      const tag = 'h' + Math.min(Math.max(level, 2), 3);
      return el(tag, { class: 'post-heading' }, block.text);
    }
    case 'para':
      return el('p', { class: 'post-para' }, block.text);
    case 'list':
      return el('ul', { class: 'post-list-block' },
        block.items.map((item) => el('li', {}, item)),
      );
    case 'quote':
      return el('blockquote', { class: 'post-quote' }, block.text);
    case 'code':
      return el('pre', { class: 'post-code' },
        el('code', {}, block.text));
    case 'hr':
      return el('hr', { class: 'post-divider' });
    case 'note':
      return el('aside', { class: 'post-note' }, block.text);
    default:
      return null;
  }
}

export function renderBlogPost(root, slug) {
  const post = POSTS.find((entry) => entry.slug === slug);

  if (!post) {
    root.replaceChildren(
      el('section', { class: 'view active blog-view' },
        el('p', { class: 'eyebrow' }, 'WRITING'),
        el('h1', {}, 'Post not found'),
        el('p', { class: 'lede' },
          el('a', { href: '/blog', class: 'text-link' }, 'Back to writing'),
        ),
      ),
    );
    return;
  }

  const header = el('header', { class: 'post-header' },
    el('div', { class: 'post-header-top' },
      el('span', { class: 'eyebrow' }, post.provenance ?? 'Writing'),
      el('span', { class: 'post-card-meta' },
        el('time', { datetime: post.date }, post.date),
        el('span', { 'aria-hidden': 'true' }, '·'),
        el('span', {}, post.readingTime ?? ''),
      ),
    ),
    el('h1', { class: 'post-title' }, post.title),
    el('p', { class: 'post-subtitle' }, post.excerpt),
    post.tags?.length ? el('div', { class: 'post-card-tags' },
      post.tags.map((t) => el('span', { class: 'tag' }, t))) : null,
  );

  const article = el('article', { class: 'post-article' },
    ...post.body.map(renderBlock),
    el('footer', { class: 'post-footer' },
      el('a', { href: '/blog', class: 'text-link' }, '← All writing'),
    ),
  );

  root.replaceChildren(
    el('section', { class: 'view active blog-view' },
      header,
      article,
    ),
  );
}
