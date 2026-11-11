# Wave-39 lane: w39-daemon-graph — C00 L7 broadcast/SSE daemon-graph ports

**Branch:** `feat/sl-w39-daemon-graph`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w39-daemon-graph`
**Cluster / pillar:** C00 L7 (score 3, residual unpaid)

## Gap

Loom permutation covers bounded models but documents _full tokio broadcast / daemon SSE
graph_ as unpaid. Expand `tests/loom_model.rs` + docs toward watcher→broadcast→SSE path
without claiming live `sl-daemon` integration under loom.

## Acceptance criteria

1. Expand `tests/loom_model.rs` with broadcast/SSE epoch permutation cases.
2. Update `scripts/loom-permutation-check.ps1` done/unpaid rows.
3. Update `docs/ops/concurrency-safety.md` daemon-graph section.
4. Ensure blocking `loom-permutation.yml` still passes.
5. CHANGELOG Unreleased bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/loom-permutation-check.ps1 -SelfCheck
cargo test loom --locked
```

## Score expectation

Evidence only; L7 pillar max — score **held**.
