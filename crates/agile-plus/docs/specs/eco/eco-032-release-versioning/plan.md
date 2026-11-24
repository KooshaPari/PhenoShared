# Plan: Release Versioning

## Objective

Establish repo-wide release versioning so active Phenotype repositories expose
consistent semver tags, generated changelogs, auditable release notes, and
protected release history.

## Scope

In scope:
- Active repos listed by AgilePlus inventory.
- Root `CHANGELOG.md` policy.
- Semver tag validation.
- Release-note generation from merged PR titles.
- Branch/tag hygiene for `main`, `release/*`, and release tags.

Out of scope:
- Archived or explicitly dormant repos.
- Rewriting historical tags.
- Paid SaaS release tooling.

## Implementation Steps

1. Inventory active repos and current release posture: tags, changelog, release
   branches, branch protection.
2. Add or normalize `CHANGELOG.md` in each active repo using Keep a Changelog
   1.1 sections.
3. Configure release-note generation from PR titles via existing OSS tooling
   (`git-cliff` or equivalent) and conventional-commit grouping.
4. Add tag and branch-protection governance checks for semver, annotated tags,
   immutable release branches, and no force-push.
5. Backfill first compliant release entries without renumbering existing tags.
6. Record exceptions with ADR references and repo-inventory markers.
