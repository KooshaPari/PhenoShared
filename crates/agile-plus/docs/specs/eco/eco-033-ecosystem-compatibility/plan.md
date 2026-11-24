# Plan

## Objective
Codify fleet toolchain compatibility and enforce pinned-version alignment.

## Scope
Rust, JavaScript/Node, Python, and Go pins for active Phenotype repositories.

## Implementation Steps
1. Inventory repo toolchain pins.
2. Create `AgilePlus/toolchain-versions.json` with canonical versions and repo assignments.
3. Add validation that compares repo pins to the matrix.
4. Wire validation into CI/local quality gates.
