# Agent Consumption Patterns

How agents should interact with each PhenoKits category.

## Quick Reference Matrix

| Category | Read | Write | Enforce | Primary Tool |
|----------|------|-------|---------|--------------|
| Templates | ✓ | Instantiate | - | `pheno new` |
| Configs | ✓ | Apply params | Validate | `parameterize.py` |
| Libs | ✓ Import | Extend | - | Cargo, pip, npm |
| Secrets | ✓ Reference | - | Scan | `gitleaks` |
| Governance | ✓ Read | Draft ADRs | - | `agileplus` |
| Security | ✓ Read | Write | Scan | `semgrep` |
| Observability | ✓ Configure | Configs | Monitor | `otel` |
| Documentation | ✓ Read | Write | - | `vitepress` |
| Scripts | ✓ Execute | Extend | - | `just`, `bash` |
| Schemas | ✓ Validate | Code gen | Type check | `cargo`, `protoc` |
| Policies | ✓ Read | Write | Enforce | `opa`, `gh` |
| Credentials | ✓ Reference | - | Rotate | `vault` |

## Detailed Patterns

### Templates

**When to use**: Starting new project/service/component

**Agent workflow**:
```bash
# 1. List available templates
pheno template list

# 2. Instantiate template
pheno new --template hexagonal-rust --name my-service --org MyOrg

# 3. Customize (user edits freely)
# Agent assists with code, not scaffolding
```

**Pattern**: User owns resulting code; agent provides assistance.

---

### Configs

**When to use**: Applying org-standard configs to project

**Agent workflow**:
```bash
# 1. Get project params
cat > params.json <<EOF
{
  "project": {"name": "my-service", "org": "MyOrg", "github_repo": "<REDACTED>/my-service"},
  "runtime": {"rust": "1.75"}
}
EOF

# 2. Apply configs
python3 scripts/utility/parameterize.py params.json configs/cicd/github-actions/ci.yml > .github/workflows/ci.yml

# 3. Add to project
git add .github/workflows/ci.yml
```

**Pattern**: Org-locked defaults; only params are project-specific.

---

### Libs

**When to use**: Reusing shared functionality

**Agent workflow**:
```toml
# Add to pyproject.toml
[project]
dependencies = [
  "phenotype-logging @ file:///path/to/PhenoKits/libs/python/phenotype-logging",
]
```

**Pattern**: Semantic versioning; breaking changes require ADR.

---

### Secrets

**When to use**: Handling sensitive data

**Agent rules**:
1. NEVER hardcode secrets in code
2. Use `SECRET:NAME` format in configs
3. Reference secrets from org vault
4. Pass as environment variables

```bash
# Wrong ❌
let api_key = "sk-12345...";

// Correct ✓
let api_key = env::var("API_KEY")
    .expect("API_KEY must be set");
```

---

### Security

**When to use**: Enforcing security policies

**Agent workflow**:
```bash
# 1. Run SAST
semgrep --config=configs/security/scanning/semgrep/rules/ .

# 2. Check policies
opa eval --bundle=configs/security/policies/opa/ .

# 3. Block if violations
if [ $violations -gt 0 ]; then
    echo "Security policy violated"
    exit 1
fi
```

---

### Schemas

**When to use**: Generating types, validating data

**Agent workflow**:
```bash
# Generate Rust types from schema
cargo add --dev apirk
apirk generate --schema schemas/api/openapi/phenotype.yaml

# Validate at compile time
cargo build
```

---

### Policies

**When to use**: Enforcing org rules

**Agent workflow**:
```bash
# Check branch protection
gh api repos/<REDACTED>/my-repo/branch-protection/main

# Enforce via OPA
opa eval --bundle=configs/policies/opa/authz.rego \
    --input '{"user": "bot", "action": "push", "branch": "main"}' \
    "data.authz.allow"
```

---

## Category-Specific Instructions

### For New Projects

1. Use templates to scaffold
2. Apply configs with params
3. Import libs for shared functionality
4. Configure observability
5. Set up security scanning
6. Document in README

### For Feature Development

1. Read schemas for type definitions
2. Follow governance patterns (ADRs)
3. Use libs for base implementations
4. Write tests using testing libs
5. Follow security guidelines

### For Infrastructure

1. Use infra configs as base
2. Apply parameterization
3. Enforce policies via OPA
4. Configure observability
5. Handle secrets via vault

---

## Anti-Patterns

### Don'ts

1. **Don't hardcode secrets** → Use `SECRET:NAME` refs
2. **Don't bypass security scanning** → Always run SAST
3. **Don't skip validation** → Use schemas for types
4. **Don't ignore ADRs** → Follow established patterns
5. **Don't copy-paste libs** → Import and extend

---

## Reference

- Templates: [../templates/README.md](../templates/README.md)
- Configs: [../configs/README.md](../configs/README.md)
- Libs: [../libs/README.md](../libs/README.md)
- Security: [../security/README.md](../security/README.md)
