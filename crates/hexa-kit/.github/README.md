# Phenotype GitHub Actions

> Reusable workflows and shared GitHub configurations

## Overview

This repository contains reusable GitHub Actions workflows used across the entire Phenotype ecosystem. By centralizing CI/CD configurations, we reduce duplication and ensure consistent quality standards.

## Reusable Workflows

### Rust CI
```yaml
uses: phenotype-dev/.github/.github/workflows/rust-ci.yml@main
with:
  rust-version: '1.75'
  test-flags: '--all-features'
```

### Python CI
```yaml
uses: phenotype-dev/.github/.github/workflows/python-ci.yml@main
with:
  python-version: '3.11'
  test-runner: 'pytest'
```

### TypeScript CI
```yaml
uses: phenotype-dev/.github/.github/workflows/typescript-ci.yml@main
with:
  node-version: '20'
```

### Go CI
```yaml
uses: phenotype-dev/.github/.github/workflows/go-ci.yml@main
with:
  go-version: '1.22'
```

## Shared Configurations

- `.github/CODEOWNERS` - Default code ownership
- `.github/dependabot.yml` - Dependency update automation
- `.github/pull_request_template.md` - PR template
- `.editorconfig` - Editor configuration
- `.pre-commit-config.yaml` - Pre-commit hooks

## License

MIT
