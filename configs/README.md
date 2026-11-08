# Configs

Parameterized configurations for tools, CI/CD, infrastructure, and runtime.

## Purpose
Standardized configurations consumed as-is with minimal parameterization.

## Mutability
| Subcategory | Mutability | Examples |
|-------------|------------|----------|
| Tooling | Parameterized | linters, formatters, IDEs |
| CI/CD | Parameterized | GitHub Actions, GitLab CI |
| Infrastructure | Parameterized | Terraform, Kubernetes, Docker |
| Application | Locked for production | runtime configs, env vars |

## Agent Pattern
Apply to repositories with parameter substitution. Org-locked defaults cannot be edited.

## Structure
```
configs/
├── tooling/          # Linters, formatters, IDEs
├── cicd/             # CI/CD pipelines
├── infra/            # Infrastructure configs
├── observability/     # Logging, metrics, tracing
└── app/              # Application configs
```

## Usage
Reference in project via git submodule or direct copy:
```bash
# Option 1: Git submodule
git submodule add <pheno-kits>/configs/cicd/github-actions .github/workflows

# Option 2: Direct copy
cp -r <pheno-kits>/configs/tooling/* .
```

## Related
- [scripts/](../scripts/) - Scripts to apply configs
- [schemas/](../schemas/) - JSON Schema for config validation

---

## Parameterization System

Configs use placeholders that are substituted during application.

### Placeholder Format

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{project.name}}` | Project kebab-case name | `my-project` |
| `{{project.org}}` | Organization PascalCase | `MyOrg` |
| `{{github.repo}}` | GitHub repository path | `<REDACTED>/my-project` |
| `{{runtime.rust}}` | Rust version | `1.75` |
| `{{runtime.node}}` | Node.js version | `20` |
| `{{runtime.go}}` | Go version | `1.22` |
| `{{runtime.python}}` | Python version | `3.12` |

### Applying Configs

```bash
# 1. Create params.json from example
cp params.example.json my-params.json
# Edit my-params.json with your values

# 2. Apply parameterization
python3 scripts/utility/parameterize.py my-params.json configs/cicd/github-actions/ci.yml

# 3. Copy to your project
cp ci.yml /path/to/project/.github/workflows/
```

### Validation

The parameterizer validates:
- Required fields present
- Pattern compliance (kebab-case, PascalCase)
- Secret format (`SECRET:NAME`)

### Secrets

Secrets should NEVER be hardcoded. Use secret references:
```json
{
  "secrets": ["SECRET:GITHUB_TOKEN", "SECRET:NPM_TOKEN"]
}
```

Agents should:
1. Read secrets from org secret manager
2. Pass as environment variables
3. Never log or commit secret values
