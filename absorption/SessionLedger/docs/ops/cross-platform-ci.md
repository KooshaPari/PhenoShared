# Cross-Platform CI Acceptance

SessionLedger PR CI is intentionally Linux-only. The default pull request
workflows run on `ubuntu-latest` because Phenotype billing policy does not allow
macOS or Windows runners for routine PR validation.

The authoritative cross-platform acceptance gate is the tag-driven release
workflow: [`.github/workflows/release.yml`](../../.github/workflows/release.yml).
A release is acceptable only when that workflow's platform matrix and dependent
smoke jobs pass.

## Release Matrix

The release build matrix must continue to include these runner families:

| Platform | Runner           | Target or artifact                             |
| -------- | ---------------- | ---------------------------------------------- |
| Linux    | `ubuntu-latest`  | `x86_64-unknown-linux-gnu`                     |
| macOS    | `macos-latest`   | `x86_64-apple-darwin`, `aarch64-apple-darwin`  |
| Windows  | `windows-latest` | `x86_64-pc-windows-msvc`, Windows MSI scaffold |

Published release artifacts:

| Artifact                                          | Produced by                                                                |
| ------------------------------------------------- | -------------------------------------------------------------------------- |
| `sl-viewer-<tag>-x86_64-unknown-linux-gnu.tar.gz` | Linux release build                                                        |
| `sl-viewer-<tag>-x86_64-apple-darwin.tar.gz`      | macOS Intel release build                                                  |
| `sl-viewer-<tag>-aarch64-apple-darwin.tar.gz`     | macOS Apple Silicon release build                                          |
| `sl-viewer-<tag>-x86_64-pc-windows-msvc.zip`      | Windows release build                                                      |
| `sl-viewer-<tag>-windows-msi-scaffold.zip`        | Windows WiX source and build notes                                         |
| `SHA256SUMS`                                      | Release checksum step                                                      |
| `session-ledger.cdx.json`                         | CycloneDX SBOM step                                                        |
| `SHA256SUMS.sigstore.json`                        | Best-effort keyless checksum signature                                     |
| `ghcr.io/kooshapari/sl-daemon:<tag>`              | OCI build + keyless cosign + attestation + release verify (canonical repo) |

## Acceptance Jobs

`release.yml` contains these cross-platform acceptance jobs:

| Job              | Runner                    | Acceptance signal                                                                                                                                                       |
| ---------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `build`          | Matrix from `release.yml` | Builds and uploads each platform archive                                                                                                                                |
| `smoke-linux`    | `ubuntu-latest`           | Downloads the Linux artifact, extracts it, and runs `sl-viewer --version`                                                                                               |
| `smoke-windows`  | `windows-latest`          | Downloads the Windows artifact, extracts it, and runs `sl-viewer.exe --version`                                                                                         |
| `release`        | `ubuntu-latest`           | Publishes only after build plus Linux and Windows smoke jobs pass                                                                                                       |
| `sign-checksums` | `ubuntu-latest`           | Attempts keyless checksum signing after publication                                                                                                                     |
| `oci-image`      | `ubuntu-latest`           | GHCR build/push + cosign sign + OCI attestation + in-workflow verify (blocking on canonical repo; explicit skip on forks); deploy gate: `scripts/oci-cosign-verify.ps1` |

macOS acceptance is a release-build acceptance signal today. Linux and Windows
also have release-artifact execution smokes before publication.

## PR Guard

The lightweight
[`.github/workflows/cross-platform-smoke.yml`](../../.github/workflows/cross-platform-smoke.yml)
workflow runs only on `ubuntu-latest`. It does not download or execute macOS or
Windows artifacts. Its purpose is to parse `release.yml` and fail if the release
matrix no longer contains `ubuntu-latest`, `macos-latest`, and `windows-latest`.

[`.github/workflows/race-smoke.yml`](../../.github/workflows/race-smoke.yml)
runs the threaded merge/OKF smoke (`tests/race_smoke.rs`) and the loom-lite
bounded-channel / cancel model (`tests/race_model.rs`) on `ubuntu-latest`,
`windows-latest`, and `macos-latest` with three repeats per runner. That gives
affordable PR coverage for concurrency determinism across host families without
executing release artifacts on every pull request. Operator notes live in
[`concurrency-safety.md`](concurrency-safety.md).

That guard keeps PR CI affordable while preventing accidental loss of the
release matrix that provides cross-platform proof.

## Default PR build-test

[`.github/workflows/cross-platform-build.yml`](../../.github/workflows/cross-platform-build.yml)
runs affordable `cargo build --locked` checks for the root workspace and the
isolated `sl-daemon` workspace on `ubuntu-latest`, `windows-latest`, and
`macos-latest`. This complements the Linux-only `build-test` job in `ci.yml`
without executing the full test matrix on every host family.

## Exotic Linux targets (PR)

The same workflow also runs an `exotic-cargo-check` job on `ubuntu-latest` that
cross-checks two non-host Linux targets with `cargo check --locked`:

| Target                      | Linker package          | What is checked                            |
| --------------------------- | ----------------------- | ------------------------------------------ |
| `aarch64-unknown-linux-gnu` | `gcc-aarch64-linux-gnu` | `-p session-ledger` and `crates/sl-daemon` |
| `x86_64-unknown-linux-musl` | `musl-tools`            | `-p session-ledger` and `crates/sl-daemon` |

These jobs intentionally skip `sl-viewer` (webkit / native UI graph). They exist
to catch arch/ABI drift (aarch64 Linux, musl) without paying for full exotic
runners or release artifact builds on every PR.
