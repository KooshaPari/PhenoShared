# Tasks: Spec-First

## WP-01 — PR Template
- Add required `spec:` field to PR template.
- Link format: `eco-<NNN>-<slug>`.

## WP-02 — CI Validation
- Reject PRs with missing or inactive spec link.
- Verify referenced spec dir exists and is `state: active`.

## WP-03 — Spec Schema Enforcement
- Validate new spec dirs contain `spec.md`, `plan.md`, `tasks.md`, `meta.json`.
- Block merge on schema violation.
