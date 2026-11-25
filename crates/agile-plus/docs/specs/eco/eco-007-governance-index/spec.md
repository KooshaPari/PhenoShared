---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
date: 2026-06-05
owner: Phenotype Agent
plan_status: NOT_STARTED
retirement_criteria: |
slug: eco-007-governance-index
spec_id: AgilePlus-eco-007
state: PENDING
status: active
superseded_by: null
title: Governance Index
type: operational
---
# Specification: Governance Index
**Slug**: governance-index | **Date**: 2026-06-05 | **State**: pending

## Problem Statement
The `eco-006-compliance-20260605.md` worklog flagged FR1 ("live governance
index of active kitty-specs") as missing. There is no single artifact in
the canonical `AgilePlus` repository that enumerates every active kitty-spec,
its current state, and its lifecycle timestamps. Auditors and fleet hygiene
agents must currently scan `AgilePlus/kitty-specs/*/meta.json` by hand,
which is error-prone and drifts between passes.

This spec closes FR1 by introducing a generated `INDEX.md` plus a CI
workflow that regenerates it on every push, so the index is always live
and provably current.

## Target Users
- Fleet hygiene agents (Phenotype governance sweep)
- Repo stewards auditing spec coverage
- Phenotype governance auditors and downstream operators
- Humans skimming the canonical repo for "what specs are live"

## Functional Requirements
- [ ] Generate a live index of all active kitty-specs under
      `AgilePlus/kitty-specs/`.
- [ ] Render each entry with a clickable link to the spec directory and
      an explicit state field (e.g. `active`, `pending`, `retired`).
- [ ] Provide an idempotent generation command (script) that walks
      `AgilePlus/kitty-specs/*/meta.json` and emits
      `AgilePlus/kitty-specs/INDEX.md`.
- [ ] CI workflow `.github/workflows/governance-index.yml` runs the
      generation command on every push to `main` and commits any
      resulting diff to `INDEX.md`.
- [ ] Index columns: `slug`, `status`, `created`, `reactivated`,
      `superseded_by`.
- [ ] Retired specs are listed with `status: retired` and a
      `superseded_by` link where present.

## Non-Functional Requirements
- `INDEX.md` is UTF-8 with no BOM.
- `INDEX.md` is regenerated on every push; no manual edits.
- Generation is deterministic (stable sort by `spec_id`).
- Generation script is portable POSIX shell or Python 3.10+ (no exotic
  runtime dependencies).
- Workflow must run on standard GitHub-hosted Linux runners (no macOS /
  Windows billed runners, per the org billing policy).

## Acceptance Criteria
- [ ] `AgilePlus/kitty-specs/INDEX.md` exists and lists every kitty-spec
      directory under `AgilePlus/kitty-specs/`.
- [ ] Each row exposes `slug`, `status`, `created`, `reactivated`,
      `superseded_by` columns.
- [ ] `.github/workflows/governance-index.yml` is present and triggers
      on `push` to `main`.
- [ ] Running the generation command locally reproduces the committed
      `INDEX.md` byte-for-byte.
- [ ] UTF-8 (no BOM) validation passes for `INDEX.md`.
- [ ] The eco-006 FR1 checkbox resolves to "implemented" once this spec
      ships.

## Constraints & Dependencies
- Scope: governance artifacts only. No product code or runtime changes.
- Standard Linux GitHub Actions runner (no billing-bearing runners).
- Existing `AgilePlus/kitty-specs/*/meta.json` schema (no migration of
  historical specs required beyond populating optional
  `reactivated` / `superseded_by` where missing).
