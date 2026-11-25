# Wave-39 lane: w39-jemalloc-hard — C00 L8 blocking jemalloc CI

**Branch:** `feat/sl-w39-jemalloc-hard`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w39-jemalloc-hard`
**Cluster / pillar:** C00 L8 (score 2, soft optional feature today)

## Gap

`jemalloc` feature + soft `ops-load` job exist (#277) but remain `continue-on-error`.
Promote to blocking PR evidence without claiming default-on production allocator or
Windows parity.

## Acceptance criteria

1. Extend `docs/ops/jemalloc.md` with hard-vs-soft matrix + blocking CI row.
2. Add blocking `.github/workflows/jemalloc-hard.yml` (SelfCheck + `cargo build --features jemalloc` on ubuntu).
3. Extend `scripts/jemalloc-check.ps1` done/unpaid gates.
4. Add or extend `tests/jemalloc_hard.rs` wrapper.
5. CHANGELOG Unreleased bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/jemalloc-check.ps1 -SelfCheck
cargo test jemalloc --locked
```

## Score expectation

Evidence toward L8 blocking jemalloc CI; conservative **+1** (2→3) if blocking gate lands.
