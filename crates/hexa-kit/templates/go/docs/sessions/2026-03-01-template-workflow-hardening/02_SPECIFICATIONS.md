# Workflow Specification

## Global (all templates)
Must be shared or kept identical:
- Branch protection audit policy contract
  - `branch-protection-audit.yml`
- Policy gate contract checks
  - `policy-gate.yml`
- Security and dependency policy artifacts
  - `.github/CODEOWNERS`
  - `.github/dependabot.yml`
  - `SECURITY.md` (repo-level)
- Required checks: `validate` and `policy-gate`.

## Project/Stack-specific
Allowed variance:
- `ci.yml`
  - only include checks required by that template language/runtime stack.
- Stack scripts and manifest validation beyond contract baseline (`scaffold-smoke.sh`, validators, etc.).

## Prohibition
Do not reintroduce language-specific checks into `policy-gate.yml` or `branch-protection-audit.yml`.
