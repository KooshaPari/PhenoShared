# Plan: Cargo Workspace Cleanup

## Objective
A known-good `repos/Cargo.toml` whose path-dep targets either exist, are extracted to a published crate, or are stubbed behind a `cfg(disabled)` gate.

## Scope
- The single `repos/Cargo.toml` workspace.
- All `crates/*/Cargo.toml` files under `repos/`.

## Implementation Steps
1. **Inventory** — `scripts/inventory-path-deps.py` walks every Cargo.toml.
2. **Classify** — For each `path` dep, decide: `present`, `missing`, `outside`.
3. **Resolve** — For each `missing`: `publish-to-cratesio`, `extract-to-workspace`, or `stub-with-cfg-disabled`.
4. **Apply** — Per-decision edits land in fresh worktrees (eco-019).
5. **Audit** — `make cargo-audit` enforces the policy on every PR.
6. **Trace** — Each decision recorded in `AgilePlus/traces/cargo-deps.json`.

## Verification
- `cargo build --workspace` exits 0 on the live tree.
- `make cargo-audit` exits 0.
- A pre-merge hook refuses any new `path = "..."` dep that is not in `cargo-deps.json`.
