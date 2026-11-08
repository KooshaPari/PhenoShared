# CI/CD Configs

Parameterized CI/CD pipeline configurations.

## Purpose
Standardized pipelines for CI, release, PR validation, and security scanning.

## Providers
- GitHub Actions (primary)
- GitLab CI (secondary)

## Structure
```
configs/cicd/
├── github-actions/
│   ├── ci.yml           # CI workflow
│   ├── release.yml      # Release workflow
│   ├── pr.yml           # PR validation
│   └── security-scan.yml # Security scanning
└── gitlab-ci/
```

## Parameters
| Parameter | Description | Required |
|-----------|-------------|----------|
| `runner` | CI runner label | No (default: ubuntu-latest) |
| `secrets` | Secret names to expose | No |
| `matrix` | Build matrix | No |

## Usage
```yaml
# In your .github/workflows/ci.yml
jobs:
  ci:
    uses: <REDACTED>/PhenoKits/configs/cicd/github-actions/ci.yml@v1
    with:
      runner: ubuntu-latest
      matrix: ["lint", "test", "build"]
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

## Related
- [scripts/quality/](../scripts/quality/) - Quality gate scripts
- [security/](../security/) - Security scanning configs
