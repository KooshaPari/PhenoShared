/**
 * Resolve Astro/VitePress base path for org deploy targets.
 *
 * - `*.phenotype.space` and custom domains: `/` (root)
 * - GitHub Pages project URL (`kooshapari.github.io/<repo>/`): `/<repo>/`
 *
 * Override with `DOCS_BASE`, `BASE_PATH`, or `VITEPRESS_BASE`.
 * Do not key off `GITHUB_ACTIONS`; CI builds for Cloudflare also run in Actions.
 */

/**
 * @param {string} repoName GitHub repo slug used for Pages subpath deploys
 * @param {{ trailingSlash?: boolean }} [options]
 * @returns {string}
 */
export function resolveSiteBase(repoName, { trailingSlash = false } = {}) {
  const explicit =
    process.env.DOCS_BASE ?? process.env.BASE_PATH ?? process.env.VITEPRESS_BASE;

  let base = '/';

  if (explicit) {
    base = explicit;
  } else if (process.env.PHENOTYPE_CUSTOM_DOMAIN === 'true') {
    base = '/';
  } else if (process.env.GITHUB_PAGES === 'true') {
    base = `/${repoName}`;
  }

  if (base !== '/') {
    base = base.startsWith('/') ? base : `/${base}`;
    base = base.replace(/\/+$/, '');
  }

  if (trailingSlash && base !== '/') {
    return `${base}/`;
  }

  return base;
}
