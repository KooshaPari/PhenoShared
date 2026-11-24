# Tasks: Release Versioning

## WP-01: Release Inventory

Audit active repos for semver tags, annotated-tag status, root `CHANGELOG.md`,
release branches, and branch-protection force-push settings.

## WP-02: Changelog Standardization

Create or normalize root `CHANGELOG.md` for every active repo using Keep a
Changelog 1.1 sections and explicit unreleased/released headings.

## WP-03: Release Notes Automation

Configure OSS-backed release-note generation from merged PR titles, grouped by
conventional-commit type/scope, with explicit exceptions for breaking and
security notes.

## WP-04: Tag and Branch Hygiene Gate

Add governance checks ensuring semver-shaped annotated tags, no lightweight
release tags, immutable release tags, and no force-push/deletion for `main` and
`release/*`.
