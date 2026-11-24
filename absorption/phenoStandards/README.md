# Phenotype Standards

> Shared configurations and standards for the Phenotype ecosystem

## Overview

Phenotype Standards provides centralized configuration files, templates, and standards used across all Phenotype repositories. This ensures consistency and reduces duplication.

## Contents

### GitHub
- `.github/CODEOWNERS` - Default code ownership
- `.github/dependabot.yml` - Dependency update automation
- `.github/pull_request_template.md` - PR template
- `.github/ISSUE_TEMPLATE/` - Issue templates

### Editor
- `.editorconfig` - Editor configuration
- `.gitignore` - Git ignore patterns

### CI/CD  
- `.pre-commit-config.yaml` - Pre-commit hooks
- `cliff.toml` - Changelog configuration
- `mise.toml` - Development environment

### Documentation
- `CONTRIBUTING.md` - Contribution guidelines template
- `SECURITY.md` - Security policy template

## Usage

### Reference from other repos

```bash
# In your repo, reference standards via symlink or copy
curl -O https://raw.githubusercontent.com/phenotype-dev/phenotype-standards/main/.editorconfig
curl -O https://raw.githubusercontent.com/phenotype-dev/phenotype-standards/main/.github/CODEOWNERS
```

### GitHub Actions Integration

```yaml
# .github/workflows/sync-standards.yml
name: Sync Standards
on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Sync Standards
        run: |
          curl -O https://raw.githubusercontent.com/phenotype-dev/phenotype-standards/main/.editorconfig
          curl -O https://raw.githubusercontent.com/phenotype-dev/phenotype-standards/main/.github/CODEOWNERS
          # etc
```

## License

MIT
