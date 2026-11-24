# Phenotype Standards Specification

> Centralized configuration and standards

## Overview

Phenotype Standards defines shared configurations used across all repositories in the Phenotype ecosystem.

## Standards

### Code Style
- **Rust:** 4-space indentation, cargo fmt
- **Python:** 4-space indentation, ruff format
- **TypeScript:** 2-space indentation, prettier
- **Go:** tabs, gofmt

### Git
- Conventional commits (feat:, fix:, docs:, etc.)
- Squash merging for PRs
- Linear history preferred

### CI/CD
- All code must pass linting
- All tests must pass
- Security scans required
- Dependency updates weekly

### Documentation
- README.md for every project
- SPEC.md for technical details
- PLAN.md for roadmap

## File Structure

```
phenotype-standards/
├── .editorconfig           # Editor configuration
├── .gitignore              # Git ignore patterns
├── .pre-commit-config.yaml # Pre-commit hooks
├── .github/
│   ├── CODEOWNERS          # Code ownership
│   ├── dependabot.yml      # Dependency updates
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── cliff.toml              # Changelog config
├── mise.toml               # Dev environment
├── README.md               # This file
└── SPEC.md                 # Technical specification
```

## Versioning

Standards follow semantic versioning:
- MAJOR: Breaking changes to standards
- MINOR: New standards added
- PATCH: Fixes to existing standards

## References

- [EditorConfig](https://editorconfig.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pre-commit](https://pre-commit.com/)
