# Site Infrastructure

`projects-landing` is the public Phenotype project hub for
`https://projects.kooshapari.com`.

## Deployments

- Production: Vercel, configured by `vercel.json`.
- Governance mirror: GitHub Pages, configured by `.github/workflows/pages.yml`.
- Build command: `bun run build`.
- Static output: `dist/`.
- Pages base path: `/projects-landing`, enabled during the Pages workflow with
  `GITHUB_PAGES=true` only (not `GITHUB_ACTIONS`). Custom-domain and
  `*.phenotype.space` builds use `/` via `packages/site-base/resolve-base.mjs`
  or `PHENOTYPE_CUSTOM_DOMAIN=true`.
- CI runtime: Node 22 plus Bun, required by Astro 6.
- GitHub Actions are pinned to full commit SHAs with tag comments for auditability.
- Pages permissions are scoped at job level rather than workflow level.

## Quality Gates

- `bun run typecheck`
- `bun run build`

The GitHub Actions workflows intentionally use Ubuntu runners only. Org Actions
billing can make checks unavailable; local validation remains the source of truth
for code readiness when billing blocks runner execution.

## Theme Contract

The site primary accent is GMK Arch teal, rooted at `#7ebab5`. Supporting colors
may deviate when they improve contrast or state recognition, but should remain
blue/teal-complementary and avoid orange as the dominant identity color.

## Internal Network UX

Internal-only links are client-revealed for trusted local contexts:

- `localhost`
- `127.0.0.1`
- `.local`
- `.ts.net`
- `.tailnet`
- `100.64.0.0/10`

Static pages cannot securely attest Tailscale membership. Treat this as a
convenience affordance, not an authorization boundary.
