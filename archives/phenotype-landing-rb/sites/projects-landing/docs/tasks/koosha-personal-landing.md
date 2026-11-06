# Koosha Personal Landing Task

## Status

Shipped initial `/koosha` route.

## Requirement

`projects.kooshapari.com` should expose a personal-level KooshaPari landing layer in
addition to the Phenotype organization catalog. The page should reuse the project graph
instead of becoming a separate, stale portfolio.

## Acceptance Criteria

- `/koosha` renders without relying on a separate service or new repository.
- The page links back to the project catalog, docs, QA, and OTel microfrontends.
- Featured systems are sourced from `data/repos.json` so the surface tracks the live
  repository graph.
- The route stays static and works in both Vercel and GitHub Pages builds.
- No secrets, private local URLs, or unpublished service names are exposed.

## Follow-Up Work

- Promote canonical personal-domain routing if `kooshapari.com` moves to this site.
- Add generated Open Graph imagery once the brand asset pipeline is centralized.
- Add visual regression coverage for `/koosha` alongside the public catalog route.
