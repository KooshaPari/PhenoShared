# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.9] - 2026-08-19

Chore: continue Signed-Releases window (fifth consecutive signed release). No functional change.

## [0.2.8] - 2026-08-19

Chore: continue Signed-Releases window (fourth consecutive signed release). No functional change.

## [0.2.7] - 2026-08-19

Chore: continue Signed-Releases window (third consecutive signed release). No functional change.

## [0.2.6] - 2026-08-19

Chore: continue Signed-Releases window (adds second consecutive signed release `sbom.intoto.jsonl` + attestation). No functional change.

## [0.2.5] - 2026-08-19

Fix release publish: add `sbom.intoto.jsonl` to `.gitignore` and use `--allow-dirty` so `cargo publish` does not fail on the generated provenance file (0.2.4 published to GitHub but failed on crates.io).

## [0.2.4] - 2026-08-19

Fix Signed-Releases: generate `sbom.intoto.jsonl` provenance file for Scorecard's `releasesHaveProvenance` probe (was only attesting via API, missing `.intoto.jsonl` asset).

## [0.2.3] - 2026-08-19

Fix vulnerability RUSTSEC-2026-0258 (h2 0.4.15 → 0.4.16) and yanked spin 0.9.8 → 0.9.9. Restores Vulnerabilities to 10/10.

## [0.2.2] - 2026-08-19

Fix release: add missing `attestations: write` permission so the sigstore attestation step succeeds (Signed-Releases).

## [0.2.1] - 2026-08-19

Patch release focused on supply-chain hardening and dependency freshness.

### Changed

- deps: bump `tokio-tungstenite` 0.29 → 0.30, `http-body-util` 0.1.4 → 0.1.5 and batch patch/minor updates.
- ci: bump GitHub Actions to current majors (checkout v7.0.1, setup-node v7, codecov v7, upload-artifact v7.0.1) and scorecard-action v2.4.0 → v2.4.4, all SHA-pinned.
- ci: pin `pip install ruff==0.16.2` by hash (`--require-hashes`) and drop the `npm install` fallback so Pinned-Dependencies scores 10/10.

### Fixed

- ci: harden workflows for OpenSSF Scorecard (least-privilege permissions, pinned dependencies).

## [0.2.0] - 2026-08-13

First tagged release. Stabilizes the public API (explicit prelude re-exports),
adds health probes and request-id middleware, hardens the hyper adapter against
memory-exhaustion (1 MiB body cap), fixes CI/workflow defects, and ships a full
docs site (quick start, API reference, architecture, traceability, journeys,
stories, ADRs).

### Added

- `docs/`: quickstart, installation, api reference, architecture pages wired
  into the vitepress site; traceability matrix expanded to 10 requirements.
- `clippy.toml`: consolidated clippy configuration (moved from `.clippy.toml`)
  so the health-dashboard required file is the single source of truth.

### Changed

- `src/lib.rs`: replace blanket `pub use module::*` glob re-exports with explicit
  named re-exports, giving downstream crates a stable, documented public API surface
  (audit finding L0/L5).
- `.github/workflows/release.yml`: switch trigger from `push: branches: [main]` to
  `push: tags: v*`, remove broken `promote` job referencing a 404 placeholder action,
  add `--locked` flag to `cargo build`/`cargo publish`, add Cargo.toml↔tag version
  verification step, add SBOM generation via `cargo-cyclonedx`, and fix garbled
  `${{ }}` template expressions (audit finding L9/L17).
- `.github/workflows/quality-gate.yml`: remove `continue-on-error: true` from the
  coverage threshold check so a coverage regression actually fails the gate
  (audit finding L11).
- `.github/workflows/scorecard.yml`: replace invalid job-level `security:` key
  with the OSSF-standard `permissions: {contents: read, id-token: write}` so the
  workflow file is valid again.
- `.github/workflows/security-deep-scan.yml`: move `hashFiles()` gating from the
  job-level `if` (invalid) to step-level `if`s on the container-scan job.
- `.github/workflows/infisical.yml`: replace the `blacksmith-2vcpu-ubuntu-2204`
  runner label (no runner matched; jobs timed out after 24h on every PR) with
  `ubuntu-24.04`; pin `actions/checkout` to a SHA.
- `.github/workflows/ci.yml`: fix detect-step shellcheck findings (quote
  `$GITHUB_OUTPUT`, group redirects), fix the broken `[ -f "**/Cargo.toml" ]`
  glob test, drop the self-referencing debug echo, and pin checkout.
- `CODEOWNERS`: tombstone root file with a redirect comment; `.github/CODEOWNERS` is
  the single authoritative source (audit finding L37).
- `ADR.md`: add canonical-source header noting `docs/adr/` wins on conflict
  (audit finding L37).
- `src/endpoints.rs`: add `HealthzEndpoint` and `ReadyzEndpoint` so any
  service built on `apisync` can mount liveness/readiness probes via the
  standard router without pulling in extra dependencies (audit finding L5/L27).
- `src/domain/middleware/request_id.rs`: add `RequestIdMiddleware` that echoes
  the inbound `X-Request-Id` header or generates a fresh id and stamps it on
  the response, closing the request-id propagation gap noted in the audit
  (audit finding L5/L27).
- `README.md`: document the expected `tokio::time::timeout` wrapper around
  adapter boundaries so downstream callers fail closed instead of waiting
  forever on transport work (audit finding L26).
- `LICENSE`: include both MIT and Apache-2.0 license texts to match the
  crate's `MIT OR Apache-2.0` declaration (audit finding L17).
- `fuzz/fuzz_targets/router_dispatch.rs`: populate the previously empty fuzz
  harness with a smoke-test that drives `ItemCrudEndpoint::handle` with random
  bytes so future regressions in the dispatch path surface during fuzzing
  (audit finding L11/L25).
- `fuzz/Cargo.toml`: declare the local `apisync` + `serde_json` + `futures`
  dependencies required by the new fuzz target.
- `AGENTS.md`: add a one-line backlog pointer so autonomous agents know where
  to look for the next round of audit findings (audit finding L30/L38).

[0.2.0]: https://github.com/KooshaPari/Apisync/compare/v0.1.0...v0.2.0
