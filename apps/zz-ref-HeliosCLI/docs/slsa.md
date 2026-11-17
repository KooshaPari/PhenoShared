# SLSA Build Attestation

This document describes the *actual* build-provenance state of this
repository. It was rewritten on 2026-08-02 because the previous version
claimed "SLSA Build L2 (achieved today)" backed by a
`.github/workflows/release-attestation.yml` that **never existed** in git
history, and referenced a `slsa-framework/slsa-github-generator/attest-build-provenance`
action that **does not exist** in any release of that project. This page now
states only what is wired in-tree, and what is not.

## What IS wired

A dedicated `attest` job (name: `attest-build-provenance`) was added to the
real release pipeline [`.github/workflows/rust-release.yml`](../.github/workflows/rust-release.yml):

- Triggered on every tag push matching `rust-v*.*.*` (the workflow trigger),
  running after the `release` job in the same workflow run.
- Downloads the same artifact set the `release` job publishes (the
  `{aarch64,x86_64}-{apple-darwin{,-app-server},unknown-linux-musl{,-app-server},pc-windows-msvc}`
  and `{*-symbols,argument-comment-lint-*,python-runtime-wheel-*}` action artifacts).
- Runs `actions/attest-build-provenance@v2.1.0` (exact version pinned) over
  those artifacts (`subject-path: "${{ github.workspace }}/dist/**"`).
- Requires `id-token: write` + `contents: read` job permissions, so provenance
  is signed with the GitHub-hosted OIDC token and stored in the
  [GitHub Artifact Attestations][ghaa] log alongside the release.

> Correction: the attestation action is **`actions/attest-build-provenance`**
> (maintained by GitHub in the `actions` org), not
> `slsa-framework/slsa-github-generator/...attest-build-provenance`, which
> does not exist. `slsa-github-generator` only ships builder/generator
> reusable workflows (e.g. `generator_generic_slsa3.yml`), not this action.

## What is NOT wired

- **First-run validation** — the `attest` job has not yet executed on a real
  release tag; until the next `rust-v*.*.*` release runs green through it, the
  provenance path is *implemented, not proven*.
- **SLSA Build L3** — no isolated/ephemeral builder
  (`generator_container_slsa3.yml` or a delegated builder), no sigstore/KMS
  re-signing of provenance, no transparency-log publication.
- **SBOM** — no CycloneDX/SPDX SBOM is emitted in any workflow.
- **Reproducible builds** — no `SOURCE_DATE_EPOCH`, no repro-check CI, and
  `CARGO_NET_OFFLINE` is not enforced in `rust-ci.yml`/`rust-release.yml`.
- **Attestation scope** — subjects are the build-job artifacts only. Files
  generated inside the `release` job (`codex-package_SHA256SUMS`,
  `config-schema.json`, `install.sh`/`install.ps1`) are not attested.

## Status table

| Requirement                                 | Status                    |
| ------------------------------------------- | ------------------------- |
| Provenance generated automatically          | ⚠ wired, unvalidated     |
| Provenance distributed alongside artifact   | ⚠ via GHAA log, in-run   |
| Build platform hosted and isolated          | ✅ GitHub Actions runners |
| Provenance authenticity (OIDC-signed)       | ✅ id-token: write        |
| Isolated builder (L3)                       | ❌ not started            |
| Provenance non-forgeable (sigstore/KMS)     | ❌ not started            |
| Transparency log publication (L3)           | ❌ not started            |
| SBOM emission                               | ❌ not started            |

## Verification

Once the first attested release exists, consumers verify with the
[GitHub CLI][gh-cli]:

```bash
gh attestation verify <artifact> --owner <org>
```

or with [`slsa-verifier`][slsa-verifier] for the downloaded provenance bundle.

## Path to SLSA Build L3

1. Switch the `attest` step to the
   `slsa-framework/slsa-github-generator/.github/workflows/generator_containerized_slsa3.yml`
   (or `generator_generic_slsa3.yml`) reusable workflow pinned to an exact
   version, so builds run on ephemeral isolated builders and provenance is
   re-signed with the builder's key.
2. Emit an SBOM (CycloneDX) in the `build` job and attest it alongside the
   binaries.
3. Enforce `CARGO_NET_OFFLINE` / vendored deps and `--locked` builds, and add a
   repro-check job.

## References

- [SLSA Framework][slsa]
- [GitHub Artifact Attestations][ghaa]
- [`actions/attest-build-provenance`][abp]
- [GitHub Actions security hardening][ghas]
- [`slsa-verifier`][slsa-verifier]

[slsa]: https://slsa.dev
[ghaa]: https://docs.github.com/en/security/supply-chain-security/artifact-attestations
[abp]: https://github.com/actions/attest-build-provenance
[ghas]: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
[gh-cli]: https://cli.github.com
[slsa-verifier]: https://github.com/slsa-framework/slsa-verifier
