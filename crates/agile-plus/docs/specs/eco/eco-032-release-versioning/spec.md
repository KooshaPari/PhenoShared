---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-032-release-versioning
spec_id: eco-032
state: PENDING
status: active
superseded_by: null
title: Release Versioning
type: operational
---
# Release Versioning

## Problem

Phenotype repos have inconsistent release hygiene. Tags are missing, irregular, or
non-semver; `CHANGELOG.md` is absent in many active repos; release notes drift
from PR titles; and force-pushes on release branches rewrite history. Consumers
cannot reason about compatibility, security patches, or upgrade paths. A
cohesive versioning policy is required to make releases auditable, comparable,
and trustworthy across the polyrepo.

## Target Users

- **Operators** integrating or upgrading Phenotype tooling who need clear
  semver signals and changelogs.
- **Maintainers** cutting releases who need deterministic tag, note, and
  branch-protection discipline.
- **Auditors / security reviewers** tracing what changed in each release.

## Functional Requirements

- **FR-1 Semver Tags.** Every release on every active repo MUST be tagged
  `vMAJOR.MINOR.PATCH` (e.g. `v1.4.2`). Pre-release tags use
  `vMAJOR.MINOR.PATCH-<pre>` (e.g. `v1.4.0-rc.1`). Tags are immutable.
- **FR-2 CHANGELOG.md per Repo.** Each active repo MUST maintain a
  `CHANGELOG.md` at root following Keep a Changelog 1.1, with sections
  `Added / Changed / Fixed / Removed / Security / Deprecated`.
- **FR-3 Release Notes from PR Titles.** Release notes MUST be auto-derived
  from merged PR titles grouped by conventional-commit scope; manual edits
  permitted only for `BREAKING CHANGE` and security callouts.
- **FR-4 No Force-Push on Release Branches.** Branches named `release/*` and
  `main` MUST be protected; force-push and deletion MUST be denied at the
  branch-protection level. Hotfix force-pushes require a documented ADR.
- **FR-5 Tag Hygiene.** Tags MUST be annotated, GPG-signed where signing is
  configured, and pushed via `git push --follow-tags`. Lightweight tags are
  forbidden on release commits.
- **FR-6 Cut Cadence.** PATCH releases cut on demand; MINOR monthly; MAJOR
  only with an approved ADR.

## Acceptance Criteria

- **AC-1 Release Coverage = 100% for Active Repos.** Every repo in the
  `active` set (per `AgilePlus/docs/repo-inventory.md`) has a current
  `CHANGELOG.md` and at least one semver tag within the last 365 days, or an
  explicit `// no-releases: <reason>` marker referencing an ADR.
- **AC-2 Tag Compliance.** CI / governance check `tag-semver` passes: no tag
  violates `vX.Y.Z` shape; no duplicate tags; no lightweight release tags.
- **AC-3 Branch Protection.** `main` and `release/*` on every active repo
  reject force-push and deletion, verified by `gh api .../protection`.
- **AC-4 Notes Provenance.** Every release's `## [vX.Y.Z]` section is
  generated from PR titles; missing-PR exceptions require an ADR reference.

## Constraints

- Backwards compatible with existing `v0.x` and `v1.x` tag history; renumbering
  forbidden.
- Lightweight repos (archived, experimental) are exempt; marked explicitly.
- No CI may run on macOS/Windows/billed runners (billing constraint).
- Wraps OSS tooling (semver regex, `git-cliff`, `standard-version`) where it
  exists; no hand-rolled equivalents.
