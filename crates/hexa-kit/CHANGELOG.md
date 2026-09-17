# Changelog

All notable changes to HexaKit are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Tier-0 governance refresh: refreshed `justfile` with build/test/lint/fmt/audit/deny/grade/ci targets.
- Tier-0 governance refresh: canonicalized `.github/workflows/{ci,audit,deny,scorecard,release}.yml` with concurrency controls and SHA-pinned actions.
- Tier-0 governance refresh: `CODEOWNERS` now lists `@<REDACTED>` and `@<REDACTED>` as owners.
- Tier-0 governance refresh: refreshed `deny.toml` with `[graph]`, `[bans]`, `[sources]`, and `[advisories]` sections.
- Tier-0 governance refresh: expanded `CODE_OF_CONDUCT.md` to full Contributor Covenant v2.1 text.
- Tier-0 governance refresh: expanded `CONTRIBUTING.md` with prerequisites, just-based workflow, and review policy.
- Tier-0 governance refresh: expanded `SECURITY.md` with supported versions, severity SLAs, and disclosure window.
- Tier-0 governance refresh: refreshed issue templates (`bug_report.md`, `feature_request.md`, `config.yml`) and `PULL_REQUEST_TEMPLATE.md`.

### Changed
- `release.yml` triggers on `v*` tag pushes only (no PRs); matrix uses `fail-fast: false` and `cargo install --locked`.
- `audit.yml` consolidated to cargo-audit + cargo-deny + cargo-machete jobs with weekly schedule.

### Deprecated

### Removed

### Fixed

### Security

## [2026-04-29] — Project hygiene pass

- Cleaned the project root docs and worklog surfaces.
- Removed stale shelf-catalog references from the active docs.
- Rewrote the local `agileplus` project docs into clean project-root guides.

[Unreleased]: https://github.com/KooshaPari/HexaKit/compare/v0.0.0...HEAD
[2026-04-29]: https://github.com/KooshaPari/HexaKit/releases/tag/2026-04-29
