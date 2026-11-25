---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-018-spec-first
spec_id: eco-018
state: PENDING
status: active
superseded_by: null
title: Spec-First
type: operational
---
# Spec-First

## Problem
Code changes ship without approved specs, breaking traceability and review discipline.

## Target Users
Maintainers, reviewers, contributors across the Phenotype monorepo.

## Functional Requirements
- FR-1: Every PR MUST link an active `eco-*` slug.
- FR-2: If no active spec exists, the PR MUST include a new spec directory under `AgilePlus/kitty-specs/`.
- FR-3: The PR template MUST include a `spec:` field enforced as required.
- FR-4: CI MUST fail when the field is empty or references a non-active slug.

## Acceptance Criteria
- AC-1: PR template enforces `spec:` link field.
- AC-2: Missing or inactive spec link blocks merge.
- AC-3: New spec dirs are validated for required files (`spec.md`, `plan.md`, `tasks.md`, `meta.json`).

## Constraints
- No code without corresponding spec.
- Specs MUST be approved before merge.
- Backward-compatible rollout per work package.
