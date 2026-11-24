# Plan — eco-014 UX/DX/AX Richness

## Objective

Establish a standing, repo-checkable standard so every public Phenotype app ships
three companion docs (`docs/ux.md`, `docs/dx.md`, `docs/ax.md`) backed by
reusable templates and a local-first checker.

## Scope

In scope:
- Three templates under `AgilePlus/docs/templates/`.
- Checker logic in the `task` runner (local, no CI billing).
- Backfill audit listing all public apps with a 3/3 or 0/3 score.

Out of scope:
- Migrating or rewriting existing app documentation content.
- Enforcing content quality beyond template-section coverage.
- CI workflow changes (billing-blocked).

## Implementation Steps

1. **Phase — Discovery.** Inventory public apps across `repos/` and tag which lack any of the three docs. Output: `backlog/apps-needing-docs.md` (one row per app).
2. **Phase — Design.** Author `ux.md`, `dx.md`, `ax.md` templates with required heading skeleton, Mermaid example, and JSON schema example. Land in `AgilePlus/docs/templates/`.
3. **Phase — Build.** Implement `task spec:check eco-014` in the `task` runner: walks every public app, asserts the three files exist, parses frontmatter + required headings, prints a per-app 3/3 table and exits non-zero on miss.
4. **Phase — Backfill.** Per-app authors copy templates and fill required sections. Tracker updated after each app lands 3/3.
5. **Phase — Validate.** Run the checker on the full org; require 100% pass before marking the spec ACCEPTED.
6. **Phase — Handoff.** Add a one-line entry in `AgilePlus/docs/governance/spec-index.md` and link templates from the global docs nav.

Dependencies: WP-01 → WP-02 → WP-03 → WP-04 (sequential; WP-04 parallelizes app backfill).
