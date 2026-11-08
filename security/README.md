# Security

Security configurations, scanning, and policies.

## Purpose
Standardize security practices across projects.

## Mutability
Enforced - Agents must enforce scanning and policy compliance.

## Structure
```
security/
├── scanning/              # SAST/DAST configs
│   ├── semgrep/
│   │   └── rules/        # Custom rules
│   ├── codeql/
│   └── bandit/
├── policies/              # Security policies
│   ├── opa/              # OPA Rego policies
│   │   ├── authz.rego
│   │   └── compliance.rego
│   ├── checkov/          # Terraform validation
│   └── tfsec/            # tfsec configs
└── hardening/             # CIS/STIG baselines
    ├── docker/
    └── kubernetes/
```

## Agent Interaction Matrix
| Action | Pattern |
|--------|---------|
| Read | Load policies during execution |
| Write | Create/update scanning configs |
| Enforce | Fail build on policy violation |

## Scanning Tools
| Tool | Type | Scope |
|------|------|-------|
| Semgrep | SAST | Code patterns |
| CodeQL | SAST | Code analysis |
| Bandit | SAST | Python security |
| Checkov | IaC | Terraform, K8s |
| Trivy | Container | Images |

## Usage
```yaml
# In CI
- name: Security Scan
  uses:<REDACTED>/PhenoKits/security/scanning/semgrep@v1
```

## Related
- [policies/](../policies/) - Policy enforcement
- [secrets/](../secrets/) - Secret scanning
- [configs/cicd/](../configs/cicd/) - CI integration
