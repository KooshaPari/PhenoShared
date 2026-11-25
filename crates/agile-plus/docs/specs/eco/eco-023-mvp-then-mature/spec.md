---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-023-mvp-then-mature
spec_id: eco-023
state: PENDING
status: active
superseded_by: null
title: MVP-Then-Mature
type: operational
---
# MVP-Then-Mature

## Problem

The ecosystem has no documented anti-regression rule for functional requirements (FRs) and specs. As features progress toward MVP, follow-up work (refactors, modernizations, dependency updates, spec consolidations) can silently regress a partially implemented FR or rewrite a spec in a way that drops already-accepted content. There is no gate that prevents an already-MVP FR from losing coverage or status, and no gate that prevents a spec from being edited in a way that contradicts its previously-accepted state.

## Target Users

- Spec authors and reviewers (PM, Analyst, Architect personas)
- Implementers and PR authors
- Autograder / CI operators
- Ecosystem stewards tracking FR coverage and spec provenance

## Functional Requirements

- FR-01 — Every PR `Changes` section MUST list each FR affected and tag it `MVP` (newly at minimum-viable) or `Mature` (strengthening an already-MVP FR). PRs that touch an FR without tagging fail lint.
- FR-02 — Autograder runs `fr-regression-check`: for every FR previously marked MVP, the implementation must still satisfy its FR-statement acceptance criteria. Any drop in coverage fails CI.
- FR-03 — Specs are append-only by default. Edits that contradict a previously-accepted section require an explicit `supersedes:` link in frontmatter and a `## Changelog` entry; bare rewrites that drop accepted content fail lint.
- FR-04 — A new spec cannot delete or invalidate content from an existing non-superseded spec. Lint refuses.
- FR-05 — `fr-regression-check` ships as a reusable task (`task fr:check`) consumable by any repo's autograder.
- FR-06 — Dashboard surfaces per-FR status (`none` / `partial` / `MVP` / `Mature`) with last-touched timestamp and regressing PR link.

## Acceptance Criteria

- AC-01 — A PR that omits FR tags in `Changes` is blocked by autograder.
- AC-02 — A PR that removes tests, code paths, or spec text relied on by a previously-MVP FR is blocked by `fr-regression-check` with a precise diff pointer.
- AC-03 — A spec edit that drops accepted content without a `supersedes:` link is blocked by `spec-lint`.
- AC-04 — A new spec referencing an existing spec's FR IDs in a contradictory way is blocked.
- AC-05 — The autograder manifest includes the `fr-regression-check` step and a `spec-lint` step.
- AC-06 — A greenfield repo can adopt the rule by adding two CI steps and a `Changes` template; documented in `docs/guides/quick-start/MVP_THEN_MATURE_QUICK_START.md`.

## Constraints

- Disk is full; no new worktrees, no git operations in this authoring pass.
- Reuse existing autograder task harness; do not fork a new CI framework.
- Bleeding-edge-first: pin newest stable lint/check task versions.
- Wrap-over-hand-roll: implement `fr-regression-check` by wrapping existing diff/coverage utilities where possible.
- Quality policy: no suppression without concrete justification + tracking reference.
- CI billing: standard Linux runners only; skip billed runners.
