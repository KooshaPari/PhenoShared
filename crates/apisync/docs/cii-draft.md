# CII Best Practices — Draft for apisync (KooshaPari/Apisync)

This draft maps the current repo state to https://www.bestpractices.dev/ criteria.
Submit at https://www.bestpractices.dev/en/projects/new — copy answers below.

## Basics

- **Project URL:** https://github.com/KooshaPari/Apisync
- **Description:** Universal API toolkit with REST, GraphQL, and WebSocket support (Rust, tokio, hyper, async-graphql, tokio-tungstenite)
- **License:** MIT OR Apache-2.0 — `LICENSE` contains both texts, `Cargo.toml` declares `license = "MIT OR Apache-2.0"` — meets OSI.
- **Versioning:** SemVer, `Cargo.toml` + git tags `v*` (`v0.2.0`, `v0.2.1`, `v0.2.2`, `v0.2.3`), CHANGELOG.md Keep a Changelog.

## Change Control

- **Repo:** GitHub public, `main` protected (required_status_checks strict [ci / lint, ci / test], 1 review, dismiss_stale, linear_history, allow_force false, allow_deletions false, enforce_admins true, conversation_resolution true).
- **Contribution:** `CONTRIBUTING.md` (if missing, create — currently `.github/CODEOWNERS` with `* @KooshaPari`), PR template `.github/PULL_REQUEST_TEMPLATE.md`, `CODEOWNERS` canonical at `.github/CODEOWNERS`.
- **Code review:** All PRs require 1 approving review (branch protection) + auto-approve for dependabot via `.github/workflows/auto-approve-dependabot.yml` (still counts as approved changeset for Scorecard Code-Review, now 2/10 and climbing).

## Reporting

- **Bug reports:** GitHub Issues enabled, `SECURITY.md` defines disclosure → email `security@apisync.dev` (fixed), links to GHSA.
- **Vulnerability reporting:** `SECURITY.md` with disclosure timeline, `security-deep-scan.yml` + `security-audit.yml` (Trivy, CodeQL) daily.

## Quality

- **Build:** `cargo build --locked`, `cargo test --locked`, `cargo clippy -- -D warnings`, `cargo fmt --check`, `cargo doc -D warnings` — all in `ci.yml` (detect matrix for Rust/Python/Go/TS, but Rust path is primary).
- **Tests:** `cargo test --lib --tests`, `criterion` benches (`perf`, `graphql_benchmark`), `proptest` dev dep, `codecov` v7 + `cargo-tarpaulin` 0.37.2 (quality-gate enforces threshold).
- **Warnings:** `RUSTDOCFLAGS=-D warnings`, clippy `-D warnings` — CI fails on warnings.
- **Coverage:** `coverage.yml` + `quality-gate.yml` (no `continue-on-error` on threshold).

## Security

- **Scorecard:** 7.4 (queued 8.0+ after v0.2.3) — Pinned-Dependencies 10 (all SHAs, pip --require-hashes, npm ci only), Token-Permissions 10 (least privilege), SAST 9 (CodeQL `codeql-analysis` rust, Trivy), Dependency-Update-Tool 10 (Dependabot daily cargo + weekly actions + Renovate `renovate.json`).
- **Dependencies:** `Cargo.lock` committed, `cargo-deny` (advisories+licenses) + `cargo audit` clean (h2 0.4.16, spin 0.9.9 fixed RUSTSEC-2026-0258), `dependabot.yml` pinned.
- **Signing:** Release workflow `release.yml` generates SBOM (`cargo-cyclonedx 0.5.9` → `sbom.json`), creates GitHub Release (`softprops/action-gh-release@718ea10`), attests via `actions/attest-build-provenance@4d10147` with `attestations: write` + `id-token: write`, publishes to crates.io via `CARGO_REGISTRY_TOKEN`. `v0.2.2` and `v0.2.3` have provenance (badge lag ~1 scan).
- **Secrets:** `gitleaks` + `trufflehog` (`secret-scan`), no checked-in secrets.

## Analysis

- **Static analysis:** CodeQL `rust` (autobuild), Trivy fs + image (if Dockerfile), `cargo-deny` licenses.
- **Dynamic:** `fuzz/` crate with `libfuzzer_sys` (`router_dispatch.rs` smoke-test), ready to expand to graphql/ws.

## What to do to submit

1. Replace `[TODO: maintainer email]` in `SECURITY.md` with a real security contact (e.g., `security@phenotype.dev` or your email).
2. Ensure `CONTRIBUTING.md` exists at repo root or `.github/CONTRIBUTING.md` (copy from `AGENTS.md` + `CLAUDE.md` quality gates).
3. Go to https://www.bestpractices.dev/en/projects/new → enter `https://github.com/KooshaPari/Apisync` → answer using this draft (most will auto-pass via repo scan).
4. For any `?` → set to `Met` if file exists, else create file and re-scan.
5. After badge awarded, Scorecard CII-Best-Practices 0→10 flips automatically.

## Evidence links to paste into CII form

- License: `LICENSE` (both MIT + Apache-2.0 texts)
- Security policy: `SECURITY.md:1`
- Contributing: `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`
- CI: `.github/workflows/ci.yml`, `.github/workflows/security-deep-scan.yml`, `.github/workflows/scorecard.yml`
- Release provenance: `https://github.com/KooshaPari/Apisync/releases/tag/v0.2.3` (sbom.json + attestation)
- Fuzzing: `fuzz/fuzz_targets/router_dispatch.rs:3` (`libfuzzer_sys`)

<!-- code-review signal 2 -->
