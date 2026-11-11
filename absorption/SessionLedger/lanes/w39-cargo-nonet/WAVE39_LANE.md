# Wave-39 lane: w39-cargo-nonet — C04 L40 cargo-fetch no-net policy

**Branch:** `feat/sl-w39-cargo-nonet`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w39-cargo-nonet`
**Cluster / pillar:** C04 L40 (score 3, residual unpaid)

## Gap

`rootless-nonet` hard evidence (#310) documents unpaid _blocking no-net for cargo-fetch
security jobs_. Add explicit blocking policy for `cargo audit`/`cargo deny` fetch paths
in `security.yml` where hermetic (document limits; no false live-runner claims).

## Acceptance criteria

1. Extend `docs/ops/sandbox-boundary.md` cargo-fetch no-net section.
2. Extend `scripts/rootless-nonet-check.ps1` or add `scripts/cargo-nonet-check.ps1 -SelfCheck`.
3. Wire blocking anchor job in `.github/workflows/security.yml`.
4. Add `tests/cargo_nonet.rs` wrapper.
5. CHANGELOG Unreleased bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/cargo-nonet-check.ps1 -SelfCheck
cargo test cargo_nonet --locked
```

## Score expectation

Evidence toward L40 cargo-fetch no-net; live rootless runner matrix unpaid — score **held**.
