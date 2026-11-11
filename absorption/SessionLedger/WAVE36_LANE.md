# Wave-36 lane: w36-oci-uncond — C06 L56 unconditional release-blocking OCI

**Branch:** `feat/sl-w36-oci-uncond`  
**Worktree:** `C:\workspace\SessionLedger-wtrees\w36-oci-uncond`  
**Cluster / pillar:** C06 L56 (OCI cosign verify on release)  
**Status:** scoped — implementation deferred  
**Wave-35 overlap:** none (#293 MCP N/A is C06 L57)

## Gap (audit-v38)

Wave-29 #246 made OCI cosign verify **release-blocking when GHCR/OIDC credentials
are present**. SCORECARD: _unconditional release-blocking OCI_ on all canonical
releases remains unpaid (credential-absent matrix still best-effort).

## Acceptance criteria

1. `.github/workflows/release.yml` — require `oci-cosign-verify` (or inline
   equivalent) on every canonical tag release path, with documented
   `continue-on-error: false` policy.
2. `docs/ops/distribution.md` — unconditional vs credential-gated matrix.
3. `scripts/oci-cosign-verify.ps1 -SelfCheck` — policy anchors + dry-run paths.
4. `packaging/README.md` cross-link if operator flow changes.
5. **Do not edit** `audit/SCORECARD.md`.

## Files to touch (exclusive)

- `.github/workflows/release.yml`
- `docs/ops/distribution.md`, `packaging/README.md`, `packaging/channels.md`
- `scripts/oci-cosign-verify.ps1`
- `CHANGELOG.md`

## Verify

```powershell
pwsh ./scripts/oci-cosign-verify.ps1 -SelfCheck
# Review release.yml policy-only diff; full cosign needs GHCR creds
```

## Score expectation

L56 already pillar max; closes operational gap toward unconditional blocking.
