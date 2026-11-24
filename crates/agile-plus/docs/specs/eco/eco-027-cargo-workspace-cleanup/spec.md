---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-027-cargo-workspace-cleanup
spec_id: eco-027
state: PENDING
status: active
superseded_by: null
title: Cargo Workspace Cleanup
type: operational
---
## Problem
A broken shared dependency in `repos/Cargo.toml` blocks every workspace consumer. OmniRoute and NetScript/MCPForge fail because they inherit a broken `focus-always-on -> phenotype-observably-macros` path dependency.

## Target Users
Rust workspace maintainers, repo stewards, CI operators, and consumers inheriting shared workspace dependencies.

## Functional Requirements
1. Inventory all path-dependency targets under `repos/`.
2. For each missing target, decide publish vs. stub vs. extract-to-workspace.
3. Add a single root `repos/Cargo.toml` audit script that fails CI if any path dependency target is missing.

## Acceptance Criteria
`repos/Cargo.toml` is in a known-good state and all consumers build.

## Constraints
No silent optionality. Preserve workspace intent. Prefer extraction or explicit stubs over broken inheritance.
