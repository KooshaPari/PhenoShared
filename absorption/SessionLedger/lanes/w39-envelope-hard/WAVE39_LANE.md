# Wave-39 lane: w39-envelope-hard — C02 L22 envelope-crypto hard evidence

**Branch:** `feat/sl-w39-envelope-hard`
**Worktree:** `C:\workspace\SessionLedger-wtrees\w39-envelope-hard`
**Cluster / pillar:** C02 L22 (score 2; soft `envelope-crypto` feature exists)

## Gap

`src/envelope.rs` + CHANGELOG stub exist but lack blocking hermetic SelfCheck +
operator SSOT clarifying non-KMS scope. Harden evidence without claiming in-tree KMS.

## Acceptance criteria

1. Extend `docs/ops/crypto-inventory.md` envelope section + done/unpaid matrix.
2. Add `scripts/envelope-crypto-check.ps1 -SelfCheck`.
3. Add `tests/envelope_crypto.rs` wrapper.
4. Add blocking `.github/workflows/envelope-crypto.yml` or anchor in `security.yml`.
5. CHANGELOG Unreleased bullet. **Do not edit** audit scorecard/traceability files.

## Verify

```powershell
pwsh ./scripts/envelope-crypto-check.ps1 -SelfCheck
cargo test envelope_crypto --features envelope-crypto --locked
```

## Score expectation

Evidence toward L22 envelope helper; conservative **+1** (2→3); KMS/sealed-secrets unpaid.
