# Research

## Directly validated findings
- Workflow file parity in `.github/workflows`:
  - `branch-protection-audit.yml` is identical across all 13 repos.
  - `policy-gate.yml` is identical across all 13 repos.
  - `ci.yml` exists in all 13 repos and differs only in stack-specific validation commands.
- API branch protection reads on `main` are consistent across all repos:
  - `required_status_checks`: `policy-gate, validate`
  - `required_approving_review_count`: `0`
  - `require_code_owner_reviews`: `false`
  - `dismiss_stale_reviews`: `true`
  - `required_linear_history`: `true`
  - `required_conversation_resolution`: `true`
  - `enforce_admins`: `true`

## Practical implication
A global/shared workflow layer is now reliable; differences should be isolated to CI stack content, not governance checks.
