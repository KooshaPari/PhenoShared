# Tasks — MVP-Then-Mature

## WP-01 — Discovery & Design (Discovery, Design)
- Inventory FR coverage tooling, spec lint, and autograder task shape across repos.
- Identify reuse points (diff/coverage utilities, Vale rules, frontmatter parsers).
- Define `Changes` template schema, FR-status data model, and `supersedes:` frontmatter contract.
- Publish ADR under `docs/changes/`.
- **Deps:** none.
- **Deliverable:** ADR + reuse map.

## WP-02 — Autograder & Spec Lint (Build)
- Implement `task fr:check` wrapping existing diff/coverage utilities; emit per-FR status JSON.
- Implement `spec-lint` step enforcing append-only edits and `supersedes:` linkage.
- Add both steps to autograder manifest.
- **Deps:** WP-01.
- **Deliverable:** working `task fr:check` + `spec-lint`; manifest updated.

## WP-03 — PR Template & Dashboard (Build)
- Author PR `Changes` template with per-FR MVP/Mature tagging.
- Add lint rule blocking PRs missing FR tags.
- Add FR-status dashboard panel; link regressing PRs.
- **Deps:** WP-01, WP-02.
- **Deliverable:** template + lint rule + dashboard panel.

## WP-04 — Validate & Handoff (Test/Validate, Deploy/Handoff)
- Author fixtures: greenfield PR, regressing PR, spec rewrite with/without `supersedes:`, contradictory new spec.
- Run autograder end-to-end on a sample repo; confirm all paths.
- Publish `docs/guides/quick-start/MVP_THEN_MATURE_QUICK_START.md`.
- Enable CI steps in canonical autograder; record adoption in `ecosystem-status.md`.
- **Deps:** WP-02, WP-03.
- **Deliverable:** green autograder run + quick-start guide + adoption entry.
