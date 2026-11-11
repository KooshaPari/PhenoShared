# Windows allocator prod rollout — runbook (W44-B2, R-2)

**Lane**: R-2 / W44-B2 / C00 L8
**Status**: code complete (C00 L8 landed via PR #360 release hardening); **rollout window gated on human approval**.
**Owner**: human-gated for: (1) picking the rollout window, (2) approving the rollback drill, (3) signing off the SLO drift report.

## What's done (machine-resolvable portion)

| Artifact                         | Path                                                                  | Status         |
| -------------------------------- | --------------------------------------------------------------------- | -------------- |
| Platform allocator feature flags | `crates/sl-daemon/Cargo.toml:18-32`                                   | ✅ on `main`   |
| SelfCheck hermetic validator     | `scripts/jemalloc-default-on-check.ps1`                               | ✅ on `main`   |
| Hard evidence runs               | `.github/workflows/jemalloc-hard.yml`, `jemalloc-default-on-hard.yml` | ✅ on `main`   |
| Policy manifest                  | `docs/ops/jemalloc-default-on.json`                                   | ✅ on `main`   |
| Runbook (this doc)               | `docs/ops/w44-b2-windows-allocator-prod.md`                           | ✅ this commit |

## What remains (human-gated)

| Step                                                                                           | Owner                    | Gating reason           |
| ---------------------------------------------------------------------------------------------- | ------------------------ | ----------------------- |
| 1. Pick the rollout window (low-traffic + on-call coverage)                                    | human                    | business calendar       |
| 2. Stage prod-canary to 10% of Windows fleet                                                   | human + automated canary | infra SRE               |
| 3. Run the rollback drill (kill binary mid-alloc, verify process exits cleanly under mimalloc) | human                    | requires prod-like load |
| 4. Review SLO drift report (p99 latency, RSS, allocations/sec)                                 | human                    | requires prod telemetry |
| 5. Promote to 100% Windows fleet                                                               | human                    | requires clean canary   |

## Machine verifier

```bash
# Hermetic self-check — confirms the allocators resolve correctly
pwsh ./scripts/jemalloc-default-on-check.ps1 -SelfCheck

# Hard evidence (Linux CI)
./scripts/jemalloc-check.sh
```

## Rollback recipe

```powershell
# Restore system allocator via opt-out feature
cargo build --manifest-path crates/sl-daemon/Cargo.toml \
  --no-default-features --features system-allocator
```

The `system-allocator` feature is retained as the prod rollback lever.

## References

- [`docs/ops/jemalloc-default-on.md`](jemalloc-default-on.md) — feature flags + opt-out
- [`scripts/jemalloc-check.ps1`](../../scripts/jemalloc-check.ps1) — hermetic validator
- [`scripts/jemalloc-default-on-check.ps1`](../../scripts/jemalloc-default-on-check.ps1) — alloc-on default check
- PR #360 — release hardening on `main`
