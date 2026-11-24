# Phenotype Shared GitHub Actions

> Reusable workflows and shared GitHub configurations for the Phenotype ecosystem

These workflows live in the [KooshaPari/PhenoShared](https://github.com/KooshaPari/PhenoShared) monorepo alongside shared crates and documentation.

[![CI](https://github.com/KooshaPari/PhenoShared/actions/workflows/ci.yml/badge.svg)](https://github.com/KooshaPari/PhenoShared/actions)

## Overview

This directory contains reusable GitHub Actions workflows used across the entire Phenotype ecosystem. By centralizing CI/CD configurations, we reduce duplication and ensure consistent quality standards.

See the root [README](../README.md) for the full inventory. Below are representative examples.

## Reusable Workflows

### CI Pipeline
```yaml
uses: KooshaPari/PhenoShared/.github/workflows/ci.yml@main
with:
  rust-version: '1.82'
  test-flags: '--all-features'
```

### Security Scan
```yaml
uses: KooshaPari/PhenoShared/.github/workflows/security-scan.yml@main
with:
  languages: rust,python
```

### Release Crates
```yaml
uses: KooshaPari/PhenoShared/.github/workflows/release-crates.yml@main
secrets:
  CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
```

### Terraform Plan
```yaml
uses: KooshaPari/PhenoShared/.github/workflows/terraform-plan.yml@main
with:
  working-directory: infra/
```

## Local Shared Configurations

- `.github/CODEOWNERS` - Default code ownership
- `.github/dependabot.yml` - Dependency update automation
- `.github/pull_request_template.md` - PR template
- `.editorconfig` - Editor configuration
- `.pre-commit-config.yaml` - Pre-commit hooks

## Full Workflow Inventory

Browse the complete set of 83 workflows in the [`.github/workflows/` directory](workflows/).

## License

MIT