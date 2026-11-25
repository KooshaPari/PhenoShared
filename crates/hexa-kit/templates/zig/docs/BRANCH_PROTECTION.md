# Branch Protection and Workflow Hardening

## Branch rules to enable on `main`

- Require pull requests before merging.
- No required approving reviews (set to 0).
- Require at least these status checks before merge:
  - `policy-gate`
  - `validate`
- Require linear history.
- Restrict force pushes and deletions.
- Enable conversation resolution before merging.
- Enforce branch protections for administrators.
- Enable strict status check enforcement.

## Workflow hardening baseline

Templates now include:

- `policy-gate` for repository contract checks.
- `ci` for scaffold validation.
- `branch-protection-audit` to validate `main` branch protection and required checks.
- Required status checks are enforced as a minimum set, with extra checks allowed.

## Remediation

- Open repository branch protection settings: [/settings/branches](/settings/branches).
- Apply or update the branch protection rule for `main` to match the contract above.
