# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Monorepo structure with 7 landing sites (6 Astro, 1 static)
- Root `Taskfile.yml` for SSOT quality gates (install, check, build, lint, clean)
- GitHub Actions CI matrix for all Astro sites
- `packages/` and `templates/` skeleton directories
- Root governance files: AGENTS.md, CLAUDE.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, SECURITY.md, LICENSE
- `justfile` mirroring Taskfile commands for developer convenience
- `deny.toml` for cargo-deny compatibility (placeholder)
- `.github/dependabot.yml` for dependency updates (cargo, pip, npm, gomod, github-actions)
- `.editorconfig`, `.gitattributes` for cross-platform consistency
- Issue templates (bug report, feature request) and PR template
