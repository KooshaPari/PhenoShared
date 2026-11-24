# W44-B3 — brew/winget publish + Authenticode/notarization live keys

**Lane**: W44-B3 — `w44-brew-winget-signing`
**R tag**: R-3 (signing keys)
**Status on main**: signing infra exists (ADR 0003, `scripts/signing-readiness-check.ps1`, `scripts/brew-winget-publish-check.ps1`, `.github/workflows/signing-hard.yml`, homebrew formula, winget installer manifest). **Live keys** are the gate.
**Gate**: **human (keys)** — needs SIGNING_CERT_P12_PATH, SIGNING_CERT_PASSWORD, BH_TOKEN, HOMEBREW_TAP_TOKEN, WINGET_TOKEN, APPLE_ID, APPLE_APP_PASSWORD, APPLE_TEAM_ID.

## Machine-resolvable portion (this commit)

- `scripts/w44-b3-signing-apply.sh` — single entry point that sources the signing env, validates the presence of each (without echoing values), and walks through macOS codesign → notary → staple → homebrew push → winget push. Each step is gated on env presence; missing keys produce a clear, actionable error listing exactly which env vars to set.
- `docs/ops/w44-b3-signing-apply.md` — operator runbook documenting the secret-vars file, the `--dry-run` flag, the rollback procedure, and the human-gated rollout window.

## Human-gated portion (NOT this commit)

- Actual .p12 issuance from Apple's Developer ID portal (or Authenticode from Sectigo/DigiCert).
- Homebrew tap push to `KooshaPari/homebrew-tap`.
- Winget push to `microsoft/winget-pkgs` (requires PR review by Microsoft staff).
- macOS notarization submission to Apple.

## Retry / TTL

Per WAVE44_PERT.md D-W44-2: if signing keys are not received within 7 days of W44-B3 start, downgrade R-3 to partial and defer the live-key portions to W45. The template infra in this commit is the durable artifact; the keys are the timed item.

## Verification

```
bash scripts/w44-b3-signing-apply.sh --dry-run
# Expected: prints "READY: W44-B3 signing template wired; awaiting live keys"
# and exits 0 without doing any signing.
```

```
bash scripts/w44-b3-signing-apply.sh
# Expected: errors with "BLOCKER: export SIGNING_CERT_P12_PATH=..." if unset.
```

## Files

- `scripts/w44-b3-signing-apply.sh` — apply script (dry-run + live)
- `docs/ops/w44-b3-signing-apply.md` — operator runbook
