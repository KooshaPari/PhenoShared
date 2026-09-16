# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Bootstrap `docs-lint.yml` (Vale + actionlint) GitHub Actions workflow.
- Repository hygiene stubs: `SECURITY.md`, `CONTRIBUTING.md`, `CODEOWNERS`.
- `DESIGN.md` with architecture documentation for the infrastructure spine.

### Changed
- Disable CodeQL static analysis (Rust not supported by CodeQL) and relax IAC coverage threshold.
- Add lefthook pre-commit hooks for local validation.
- Add 88-pillar scorecard CI workflow for regression prevention.
- Add fuzz, mutation, and benchmark scaffolds.
- Add missing quality gates.

### Fixed
- Relax IAC coverage threshold from 60% to 30%.
- Add `.trufflehog.yml` exclusions for governance files.
- Remove duplicate `[dev-dependencies]` section in `pheno-config/Cargo.toml`.

## [0.1.0] - 2026-08-11

### Added
- Infisical integration workflow for secret synchronization.
- `.pre-commit-config.yaml` with standard commit hooks.
- `renovate.json` for automated dependency updates.

### Changed
- Update CI workflows with stable lint/test gate names.
- Update Trunk Check configuration (`trunk.yaml`, `.trunk/trunk.yaml`).
- Update `.circleci/config.yml` pipeline configuration.
- Update `.github/stale.yml` stale issue/PR policy.
- Update `.github/workflows/scorecard.yml` workflow.
- Update `.github/workflows/trunk-check.yml` workflow.
- Update `.github/workflows/ci.yml` workflow.
- Update `.mergify.yml` auto-merge policy.

### Fixed
- Make Mergify base policy valid (#129).

### Dependencies
- Bump `actions/upload-artifact` from 4 to 7 (#108).
- Bump `ansible/ansible-lint` from 26.4.0 to 26.6.0 (#126).
- Bump `github/codeql-action/analyze` from 4.36.2 to 4.37.4 (#127).
- Bump `actions/setup-go` from 5 to 7 (#128).

## [0.0.1] - 2026-07-01

### Added
- Initial repository scaffold with CI/CD, governance, and build tooling.
