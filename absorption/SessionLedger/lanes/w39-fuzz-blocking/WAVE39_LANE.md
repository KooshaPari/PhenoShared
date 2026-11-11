# Wave-39 lane: w39-fuzz-blocking — C07 L67 blocking sustained fuzz

**Branch:** `feat/sl-w39-fuzz-blocking`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w39-fuzz-blocking`
**Cluster / pillar:** C07 L67 (score 2, soft cadence today)

## Gap

Soft `fuzz-cadence.yml` + SelfCheck (#266) remain `continue-on-error`. Add blocking
sustained fuzz smoke on PR (bounded runtime) without claiming multi-hour corpus triage.

## Acceptance criteria

1. Extend `docs/ops/fuzz-cadence.md` with blocking vs soft matrix.
2. Add blocking `.github/workflows/fuzz-blocking.yml` (SelfCheck + bounded `cargo fuzz` run).
3. Extend `scripts/fuzz-cadence-check.ps1` done/unpaid rows.
4. Extend `tests/fuzz_cadence.rs` if needed.
5. CHANGELOG Unreleased bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/fuzz-cadence-check.ps1 -SelfCheck
cargo test fuzz_cadence --locked
```

## Score expectation

Evidence toward L67 blocking sustained fuzz; conservative **+1** (2→3).
