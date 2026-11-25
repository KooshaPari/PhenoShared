# Wave-37 lane: w37-2fa-ssot — C04 L36 maintainer 2FA policy SSOT

**Branch:** `feat/sl-w37-2fa-ssot`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w37-2fa-ssot`
**Cluster / pillar:** C04 L36 (score 0)

## Gap

Org 2FA cannot be proven from checkout. Add explicit maintainer 2FA policy SSOT

- SelfCheck with NOT_VERIFIABLE_IN_REPO human attestation row (no false claims).

## Acceptance criteria

1. Add `docs/ops/maintainer-2fa.md` policy SSOT.
2. Add `scripts/maintainer-2fa-check.ps1 -SelfCheck`.
3. Cross-link `SECURITY.md` + `CONTRIBUTING.md`.
4. Optional `tests/maintainer_2fa.rs` wrapper.
5. CHANGELOG bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/maintainer-2fa-check.ps1 -SelfCheck
```

## Score expectation

Evidence toward L36; score held until human/org attestation recorded (conservative).
