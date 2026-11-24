---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-033-ecosystem-compatibility
spec_id: eco-033
state: PENDING
status: active
superseded_by: null
title: Ecosystem Compatibility
type: operational
---
## Problem
Fleet toolchains drift: Rust 1.x pins vary, Node 18/20/22 coexist, Python 3.11/3.12 differ, and Go 1.22/1.23 pins are inconsistent.

## Target Users
Repo maintainers, release agents, CI owners.

## Functional Requirements
- Maintain one `AgilePlus/toolchain-versions.json` listing canonical Rust, Node, Python, and Go versions plus repo-to-version assignments.
- CI verifies each repo pinned version matches the matrix.

## Acceptance Criteria
- Zero toolchain drift on `main` across all matrix-covered repos.

## Constraints
- Existing repo pins remain explicit.
- Fail loudly on mismatch.
- Linux CI path is authoritative when billed runners are unavailable.
