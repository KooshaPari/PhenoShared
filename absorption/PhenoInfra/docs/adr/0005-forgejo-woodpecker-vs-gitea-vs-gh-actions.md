# ADR 0005 — Forgejo + Woodpecker vs. Gitea vs. GitHub Actions

- **Status:** Proposed (stub)
- **Date:** 2026-04-24

## Context

Need a self-hosted CI+git stack. Options: Gitea (original), Forgejo (community fork), Gitea Actions, Woodpecker, Drone, GitHub Actions (paid).

## Decision (outline)

- Forgejo for git host — community governance, active maintainer set.
- Woodpecker for CI — simple YAML, Docker/podman runner, label-based routing.
- GitHub remains a public mirror for discoverability; billing-bound CI stays off.

## Consequences (outline)

- Two services to operate vs. one monolith.
- Woodpecker's plugin ecosystem smaller than GH Actions; acceptable for our needs.

## Alternatives (outline)

- Gitea Actions — rejected: project governance concerns post-Forgejo fork.
- Drone — rejected: Harness acquisition uncertainty.
- Jenkins — rejected: operational cost per ADR 0001 analysis.

## Related

- ADR 0007 (runner labels), ADR 0002 (backbone hosting)

> **TODO:** Flesh out rationale with benchmarks and governance links before marking Accepted.
