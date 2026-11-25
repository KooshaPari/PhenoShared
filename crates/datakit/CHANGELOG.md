# Changelog

All notable changes to DataKit are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). This baseline was
reconstructed from the initial repository creation.

## [Unreleased]

### Added
- Initial repository scaffolding with standard community files.
- `.editorconfig` for consistent editor settings.
- `.pre-commit-config.yaml` for pre-commit hooks (Rust, hygiene, secrets).
- `CHANGELOG.md` for tracking notable changes.
- `CONTRIBUTING.md` with development setup and submission guidelines.
- `SECURITY.md` for vulnerability reporting policy.
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1).
- `CLAUDE.md` for AI-assisted development context.
- `.mergify.yml` for automated PR management.
- `CODEOWNERS` for review assignments.

## [v0.1.0] - 2026-07-17

### Added
- Initial `DataStream<T>` and `Pipeline<T, U>` abstractions.
- Basic pipeline transformation test.
- CI workflow for build and test.

[v0.1.0]: https://github.com/KooshaPari/DataKit/releases/tag/v0.1.0
