# Wave-38 lane: w38-rootless-hard — C04 L40 hard rootless/no-net CI evidence

**Branch:** `feat/sl-w38-rootless-hard`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w38-rootless-hard`
**Cluster / pillar:** C04 L40 (score 3, residual unpaid)

## Gap

Sandbox boundary SelfCheck is blocking but hard rootless-only runner matrix and
blocking no-net for cargo-fetch security jobs remain unpaid. Add explicit hard
rootless/no-net CI evidence (docs + blocking workflow + security/ci anchors)
without false claims about live runner enforcement.

## Acceptance criteria

1. Add `scripts/rootless-nonet-check.ps1 -SelfCheck`.
2. Add blocking `.github/workflows/rootless-nonet.yml` (no `continue-on-error`).
3. Extend `docs/ops/sandbox-boundary.md` with **Hard rootless / no-net CI** section (done/unpaid gates).
4. Add `tests/rootless_nonet.rs` pwsh SelfCheck wrapper.
5. Cross-reference anchors in `security.yml` + `ci.yml`.
6. CHANGELOG Unreleased bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/rootless-nonet-check.ps1 -SelfCheck
cargo test --test rootless_nonet --locked
```

## Score expectation

Evidence toward L40 hard rootless/no-net CI; score held until live runner matrix
and blocking no-net for cargo-fetch jobs land (conservative).
