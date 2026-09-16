# Dependabot & CODEOWNERS Coverage Audit

**Date:** 2026-05-05
**Scope:** /Users/<REDACTED>/CodeProjects/Phenotype/repos/

---

## AUDIT 1: Dependabot Coverage

### Repos WITH Package Managers but NO Dependabot

| Repo | Package Manager |
|------|-----------------|
| agileplus-agents/ | cargo |
| agileplus-mcp/ | pip |
| AgilePlus/ | cargo |
| bdd-integration/ | cargo |
| dispatch-mcp/ | pip |
| docs/ | npm |
| pheno-cli/ | go |
| PhenoLang/ | go |
| python/ | pip |
| rust/ | cargo |

**Total: 10 repos missing Dependabot**

### Repos WITH Dependabot Configured

92 repos have Dependabot configured (see full list in findings directory).

---

## AUDIT 2: CODEOWNERS Coverage

### Repos MISSING .github/CODEOWNERS

| Repo |
|------|
| __pycache__/ |
| agentops-policy-federation/ |
| agileplus-agents/ |
| agileplus-landing/ |
| agileplus-mcp/ |
| AgilePlus-wtr/ |
| AgilePlus/ |
| apps/ |
| bdd-integration/ |
| byteport-landing/ |
| crates/ |
| default/ |
| dispatch-mcp/ |
| fleet-audit/ |
| frontend/ |
| harnesses/ |
| hwledger-landing/ |
| kitty-specs/ |
| libs/ |
| netweave-final2/ |
| node_modules/ |
| Observably/ |
| pheno-cli/ |
| PhenoContracts/ |
| PhenoControl/ |
| PhenoEvents/ |
| PhenoLang/ |
| PhenoSchema/ |
| phenotype-icons/ |
| phenotype-omlx/ |

**Summary:** Extensive CODEOWNERS gap across the ecosystem.

---

## Action Items

1. **Dependabot Gap (10 repos):** Add `.github/dependabot.yml` to:
   - Rust/Cargo repos: `agileplus-agents/`, `AgilePlus/`, `bdd-integration/`, `rust/`
   - Python repos: `agileplus-mcp/`, `dispatch-mcp/`, `python/`
   - Go repos: `pheno-cli/`, `PhenoLang/`
   - npm repo: `docs/`

2. **CODEOWNERS Gap:** Add `.github/CODEOWNERS` to all listed repos, particularly canonical repos (`AgilePlus/`, `PhenoLang/`, `pheno-cli/`, etc.)

---

## Raw Data

### Dependabot-Negative Repos (package manager detected, no dependabot.yml)

```
agileplus-agents/: cargo, NO DEPENDABOT
agileplus-mcp/: pip, NO DEPENDABOT
AgilePlus/: cargo, NO DEPENDABOT
bdd-integration/: cargo, NO DEPENDABOT
dispatch-mcp/: pip, NO DEPENDABOT
docs/: npm, NO DEPENDABOT
pheno-cli/: go, NO DEPENDABOT
PhenoLang/: go, NO DEPENDABOT
python/: pip, NO DEPENDABOT
rust/: cargo, NO DEPENDABOT
```
