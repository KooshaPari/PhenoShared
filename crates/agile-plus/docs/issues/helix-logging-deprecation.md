# Issue: Archive or remove helix-logging and helix-tracing crates

**Severity:** Medium
**Category:** Tech Debt
**Reporter:** OWL (external audit)
**Date:** 2026-05-02

## Summary

`PhenoObservability/crates/helix-logging` and `helix-tracing` have been absorbed into `tracely-core` (per comments in `tracely-core/Cargo.toml`). The original crates are dead code — no other crate depends on them, and `tracely-core` replaces both.

Leaving them in the workspace causes confusion for new contributors and inflates build times.

## Evidence

`tracely-core/Cargo.toml`:
```toml
# Core tracing (from helix-tracing)
# Core logging (from helix-logging)
```

`grep` of all `Cargo.toml` files confirms zero dependencies on `helix-logging` or `helix-tracing`.

## Recommended Fix

1. Move both crates to `PhenoObservability/crates/_archived/helix-logging/` and `/_archived/helix-tracing/`
2. Add a README in `_archived/` explaining they were merged into `tracely-core` on 2026-05-02
3. Remove from workspace `Cargo.toml` members list

## Acceptance Criteria

- [ ] `helix-logging` and `helix-tracing` removed from workspace members
- [ ] Archived with README explaining the merge
- [ ] `cargo build -p tracely-core` still passes
- [ ] No remaining references to either crate in other `Cargo.toml` files
