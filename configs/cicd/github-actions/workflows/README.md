# GitHub Workflow Templates

Centralized CI/CD workflow **copy-source examples** for Phenotype projects.

> **Canonical reusables live elsewhere — do not treat these as the source of truth.**
> For the org's federated governance checks, `uses:` the canonical reusable
> workflows directly rather than copying the templates here (which can drift):
> - **cargo-deny** (mechanism): `<REDACTED>/phenotype-tooling/.github/workflows/reusable/cargo-deny.yml@main`
>   — its policy baseline (`deny.toml`) is owned by `phenotype-org-governance` (the enforcement repo).
> - **trufflehog** (mechanism): `<REDACTED>/phenotype-tooling/.github/workflows/reusable-trufflehog.yml@main`.
> The files in this directory are *starting-point examples* for repos that need a
> bespoke pipeline — they are not live workflows (this is a `configs/` tree, not
> `.github/workflows/`) and they are not the federated source of truth.

## Usage

Prefer referencing the canonical reusables above. These templates are for
copy-and-adapt when a repo needs a bespoke pipeline.

### Referencing Templates

```yaml
# In your project .github/workflows/ci.yml
on:
  push:
    branches: [main]
  pull_request:

jobs:
  quality:
    uses: <REDACTED>/template-commons/.github/workflows/quality-gate.yml@main
```

## Available Templates

| Template | Purpose | Language |
|----------|---------|----------|
| `ci.yml` | Validation and smoke tests | All |
| `quality-gate.yml` | Code quality checks | Rust, Python |
| `rust-template.yml` | Full Rust CI pipeline | Rust |
| `python-template.yml` | Full Python CI pipeline | Python |
| `typescript-template.yml` | Full TypeScript CI pipeline | TypeScript |
| `release-template.yml` | Release to crates.io, PyPI, GitHub | All |
| `security-template.yml` | Security scanning | All |
| `benchmark-template.yml` | Performance benchmarks | Rust, Python |
| `sast-full.yml` | Full SAST scan | All |
| `sast-quick.yml` | Quick SAST scan | All |
| `branch-protection-audit.yml` | Branch protection checks | All |
| `policy-gate.yml` | Policy compliance checks | All |

## Template Details

### quality-gate.yml

Runs on every push/PR:
- Format check (cargo fmt / ruff format)
- Lint check (clippy / ruff)
- Tests (cargo test / pytest)
- Security audit (cargo audit / pip-audit)

### release-template.yml

Runs manually via `workflow_dispatch`:
- Validates version format
- Publishes Rust crates to crates.io
- Publishes Python packages to PyPI
- Creates GitHub release with changelog

Inputs:
- `version`: Version to release (e.g., v1.0.0)
- `dry_run`: Dry run mode (default: false)

### security-template.yml

Runs on:
- Manual trigger
- Daily schedule (2 AM UTC)
- Every push to main
- Every PR

Checks:
- Rust: cargo-audit, cargo-deny
- Python: pip-audit, safety
- SAST: Semgrep, Trivy
- Secrets: gitleaks

### benchmark-template.yml

Runs on:
- Manual trigger
- Every push to main
- Every PR to main

Features:
- Runs benchmarks
- Uploads results as artifacts
- Compares with main branch on PRs
- Comments on PR with results

## Environment Variables

All templates support these environment variables:

```yaml
env:
  RUST_BACKTRACE: 1
  CARGO_TERM_COLOR: always
```

## Permissions

Templates request minimal permissions:
- `contents: read` - For checkout
- `security-events: write` - For SARIF uploads
- `id-token: write` - For OIDC publishing (release only)
- `contents: write` - For releases only

## Adding New Templates

1. Create template in this directory
2. Document in this README
3. Add to `AGENTS.md` if it requires special handling
4. Test with a sample project

## See Also

- [E2E Workflows](../workflows/README.md) - Repository management scripts
- [pheno-cli](../pheno-cli/) - CLI for project operations
