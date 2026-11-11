# Hermetic and offline build checks

SessionLedger's current offline evidence is scoped to `crates/sl-daemon`. The
check proves that Cargo can resolve the committed lockfile, fetch dependencies
up front, and then build the daemon without network access:

```powershell
pwsh ./scripts/hermetic-check.ps1
```

The script runs from `crates/sl-daemon`:

1. `cargo fetch --locked`
2. `cargo build --locked --offline`

If the offline build needs the network, Cargo fails before producing the daemon
binary and the script reports the failure as blocking. This catches missing
lockfile updates, dependency feature changes that were not fetched, and registry
access during the build phase.

## CI policy

`.github/workflows/hermetic.yml` runs this check on Ubuntu for pushes and pull
requests. It is a dependency-offline gate, not a claim that release builds are
fully hermetic across every host and target. The same workflow also runs
`scripts/repro-check.ps1 -PolicyOnly` so release packaging keeps exporting
`SOURCE_DATE_EPOCH` without a second compile matrix.

A second job rebuilds `sl-daemon` inside the Repository-maintained builder image
recorded in [`hermetic-builder.json`](hermetic-builder.json). The GHCR manifest
digest must match the `container.image` reference in the workflow; never replace
it with a mutable tag.

## Reusable hermetic build workflow

The isolated container offline rebuild is extracted into
[`.github/workflows/reusable-hermetic-build.yml`](../../.github/workflows/reusable-hermetic-build.yml).
The caller [`.github/workflows/hermetic.yml`](../../.github/workflows/hermetic.yml)
invokes it via `workflow_call` with a **full commit SHA** pin and a
`builder_image_digest` input that must match [`hermetic-builder.json`](hermetic-builder.json).
See [`reusable-hermetic-pin.md`](reusable-hermetic-pin.md) for the bump procedure.

Machine-verify the caller provenance contract (no cargo, no network):

```powershell
pwsh ./scripts/reusable-provenance-check.ps1 -SelfCheck
```

This is partial reusable-workflow provenance evidence (C06 L53), not SLSA Build
Level 3 signing for nested workflow calls.

## Repository-maintained builder image

`ci/hermetic-builder/Containerfile` starts from an exact `rust:1.87-slim`
digest and installs **Git + CA roots** (`ca-certificates`). GitHub starts the
job inside this image before `actions/checkout`, so Git must be available or
checkout falls back to a less reliable REST path. The image retains an immutable
Rust base and is consumed only by final GHCR manifest digest.

`.github/workflows/hermetic-builder.yml` publishes a SHA-tagged
`ghcr.io/kooshapari/sessionledger-hermetic-builder` whenever the builder
definition changes. After it succeeds, copy the reported manifest digest into
both `hermetic-builder.json` and `hermetic.yml`; the latter is the only image
reference used by the blocking offline container gate. The isolation SelfCheck
validates the Rust-base digest, Git/CA installation, publish workflow, and
consuming digest without contacting a registry.

The optional root-package check can be run locally with:

```powershell
pwsh ./scripts/hermetic-check.ps1 -IncludeRootPackage
```

That mode builds `session-ledger` with `--package session-ledger` after a root
workspace fetch. CI keeps the required gate focused on `sl-daemon` because the
root workspace also contains desktop packaging dependencies that are governed by
separate release checks.

## What this does not prove

This policy does not meet SLSA Build Level 3. Remaining gaps include:

- no pinned immutable runner image or system package snapshot;
- no vendored dependency directory checked into the repository;
- no isolated rebuild on two independent builders;
- no proof that the linker, OS libraries, or archive metadata are deterministic;
- no protected release environment requiring maintainer approval for bypasses.

Treat this as stronger offline evidence for `sl-daemon` and as a prerequisite
for future hermetic release work, not as a SLSA L3 attestation.

## Environment isolation checklist (SLSA L3 gaps)

Use this checklist when closing C06 environment-isolation / OCI gaps. Items
marked **done** are already in-tree; the rest stay unpaid until operators wire
GitHub Environments and harden runners.

Machine-verify the checklist anchors and done-gate evidence paths (no cargo
build, no network):

```powershell
pwsh ./scripts/slsa-isolation-check.ps1 -SelfCheck
```

`-SelfCheck` asserts this section stays present, done rows stay marked **done**,
unpaid L3 rows stay documented, `hermetic-builder.json` digests match
`hermetic.yml`, the isolated container rebuild job remains wired, and
`release.yml` keeps canonical-repo blocking `oci-image` plus the verify-on-deploy
pointer. It does **not** claim SLSA Build Level 3. Optional soft CI runs the
same SelfCheck from `hermetic.yml` (`continue-on-error: true`) for isolation only.
The legacy `scripts/hermetic-isolation-check.ps1` wrapper delegates here.

Protected GitHub Environments and publish-job `environment:` binding are tracked
in the dedicated [`slsa-protected-environment.md`](slsa-protected-environment.md)
checklist (honest unpaid rows — not full L3 attestation). Blocking CI runs the
protected-environment SelfCheck from `security.yml`:

```powershell
pwsh ./scripts/slsa-protected-env-check.ps1 -SelfCheck
```

| Gate                                                  | Status                 | Evidence / next step                                                                                                                                                              |
| ----------------------------------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Offline `sl-daemon` fetch+build                       | **done**               | `scripts/hermetic-check.ps1` + `hermetic.yml`                                                                                                                                     |
| Repository-maintained digest-pinned builder image     | **done**               | `ci/hermetic-builder/Containerfile` + `hermetic-builder.json` + container job                                                                                                     |
| `SOURCE_DATE_EPOCH` release wiring                    | **done**               | `repro-check.ps1 -PolicyOnly`                                                                                                                                                     |
| GHCR build + keyless cosign + attest + release verify | **done**               | `release.yml` `oci-image` (blocking on canonical repo; explicit skip on forks)                                                                                                    |
| Verify-on-deploy (cosign / attestation)               | **done (deploy-time)** | `scripts/oci-cosign-verify.ps1` + [distribution.md](distribution.md#verify-an-oci-image-cosign)                                                                                   |
| Isolated container rebuild evidence                   | **done**               | `reusable-hermetic-build.yml` + `hermetic.yml` `sl-daemon-offline-container` caller (digest-pinned GHCR image; **single builder** — not two-independent-builder L3)               |
| Reusable-workflow caller SHA pin                      | **done**               | `reusable-hermetic-build.yml` + [`reusable-hermetic-pin.md`](reusable-hermetic-pin.md) + `scripts/reusable-provenance-check.ps1 -SelfCheck`                                       |
| Protected GitHub Environment for releases             | unpaid                 | [`slsa-protected-environment.md`](slsa-protected-environment.md) SSOT — create `release` Environment with required reviewers; bind `oci-image` / publish jobs with `environment:` |
| Immutable / ephemeral runners for release             | unpaid                 | Pin self-hosted or hardened runners; avoid mutable `ubuntu-latest` as sole L3 claim                                                                                               |
| Vendored deps + two-builder rebuild                   | unpaid                 | Vendor or remote-cache proof; rebuild on a second independent builder                                                                                                             |
| System package / linker snapshot                      | unpaid                 | Lock OS packages inside the builder image beyond the Rust toolchain pin                                                                                                           |
| SLSA L3 isolation SelfCheck                           | **done**               | `scripts/slsa-isolation-check.ps1 -SelfCheck` (+ soft CI job; `hermetic-isolation-check.ps1` delegates)                                                                           |
| SLSA protected-environment SelfCheck                  | **done**               | [`slsa-protected-environment.md`](slsa-protected-environment.md) + `scripts/slsa-protected-env-check.ps1 -SelfCheck` (+ blocking `security.yml` job)                              |

**Policy:** On the canonical repository, `oci-image` is release-blocking when
`packages:write` and OIDC are available. Forks skip OCI with an explicit reason
so unsigned portable Releases remain valid. Deploy-time verify
(`oci-cosign-verify.ps1`) remains the operator gate when pulling by digest.
Portable archives + `SHA256SUMS` remain the supported path when OCI provenance
is missing or skipped.

## Builder pin

[`hermetic-builder.json`](hermetic-builder.json) records the MSRV, immutable
GHCR builder digest, exact upstream `rust:1.87-slim` digest, and offline target
path. `scripts/hermetic-check.ps1` asserts the host `rustc` meets the pinned
MSRV before running the offline build.

<!-- Isolated container rebuild evidence | **done** -->
<!-- Offline `sl-daemon` fetch+build | **done** -->
<!-- Reusable-workflow caller SHA pin | **done** -->
<!-- Repository-maintained digest-pinned builder image | **done** -->
<!-- `SOURCE_DATE_EPOCH` release wiring | **done** -->
<!-- Verify-on-deploy (cosign / attestation) | **done (deploy-time)** -->
<!-- SLSA L3 isolation SelfCheck | **done** -->
