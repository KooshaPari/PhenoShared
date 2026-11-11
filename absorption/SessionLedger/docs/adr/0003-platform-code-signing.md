# ADR 0003: Platform code-signing and notarization remain deferred

- Status: Accepted
- Date: 2026-07-13
- Decision owners: SessionLedger maintainers
- Related: `docs/ops/distribution.md`, issue #66, ADR 0001

## Context

SessionLedger ships portable, unsigned desktop archives through GitHub Releases.
Release CI already provides supply-chain evidence that does **not** require Apple
or Microsoft signing credentials:

| Trust path                                 | What it proves                                | Status                              |
| ------------------------------------------ | --------------------------------------------- | ----------------------------------- |
| `SHA256SUMS`                               | Per-asset digest list                         | Published on every `v*` tag         |
| Cosign keyless `SHA256SUMS.sigstore.json`  | Checksums signed by the tag workflow identity | Best-effort (Sigstore availability) |
| GitHub build provenance (`gh attestation`) | Artifact digest bound to repo/workflow/commit | **Blocking** on canonical releases  |
| CycloneDX SBOM                             | Dependency inventory                          | Published on every `v*` tag         |

Platform-native trust is separate:

- **macOS** — Developer ID signing, `notarytool` notarization, stapling
- **Windows** — Authenticode (`signtool`) for `sl-viewer.exe` and future MSI

Those paths require maintainer-held certificates, secure secret storage, and
clean-host install validation on each platform. The repository does not have
those credentials in CI today. ADR 0001 also rejects silent background updates
until signature-verified replacement is possible.

## Decision

**Apple notarization and Windows Authenticode remain explicitly deferred (N/A
for the current portable release channel).** The product's production trust
model is:

1. Download from the canonical GitHub Release for the intended tag.
2. Verify `SHA256SUMS` (and cosign bundle when present).
3. Verify GitHub build provenance with `gh attestation verify`.
4. Run the unsigned binary with documented Gatekeeper / SmartScreen mitigations
   for internal testing only.

No CI job will claim platform-native signing until credentials and clean-host
smoke evidence exist. Packaging scaffolds (WiX MSI, `.app` Make targets,
AppImage/deb scripts) may continue as **unsigned** build artifacts.

### What is in scope now

- Documented deferral with reconsider triggers (this ADR).
- Blocking GitHub OIDC build provenance on canonical releases.
- Best-effort cosign checksum signing without blocking publication.
- Install/uninstall lifecycle scripts and OCI HEALTHCHECK for daemon images.

### What is out of scope until credentials land

- `codesign` / `notarytool` / stapling for macOS `.app` bundles.
- Authenticode signing for Windows `.exe` / MSI.
- SmartScreen- or Gatekeeper-trusted end-user installs without manual override.
- In-app or silent auto-update (see ADR 0001).

## Consequences

- Release notes and `distribution.md` continue to describe unsigned portable
  artifacts and manual verification steps.
- Internal testers accept Gatekeeper / SmartScreen friction or build from source.
- Supply-chain audit evidence focuses on Sigstore + GitHub attestations + SBOM,
  not platform code signatures.
- Future signing work must add per-platform clean-host install smoke before the
  deferral is reversed.

## Reconsider when

Revisit platform signing only when **all** of the following are true:

1. Maintainer-held Apple Developer ID and/or Windows Authenticode certificates
   are available to CI through an approved secret store.
2. A named owner commits to clean-host install → launch → uninstall smoke on
   macOS and Windows for signed artifacts.
3. ADR 0001 auto-update requirements (signature-mandatory metadata, rollback,
   atomic replacement) are satisfied **or** remain explicitly out of scope while
   only first-install signing is added.

Until then, record platform signing as **deferred / N/A** rather than an open
implementation gap without credentials.

## Signing readiness checklist

Operational detail — current unsigned artifact matrix, unpaid credential gates,
and what CI would need when certificates land (without storing secrets in the
repo) — lives in
[`docs/ops/signing-readiness.md`](../ops/signing-readiness.md).

Machine-checkable anchors (ADR + `release.yml` unsigned MSI/PKG path):

```powershell
pwsh ./scripts/signing-readiness-check.ps1 -SelfCheck
```
