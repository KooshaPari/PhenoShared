# Testing / Verification

- `git status`, `git branch -vv`, and `git rev-list --left-right` before publication.
- Gitleaks clean scan over each unpublished history set.
- Atomic push with no force or deletion.
- `git ls-remote` verification of each namespaced ref after push.
- Airlock snapshot verification for dirty worktrees.
- Registry boundary review before archive/import decisions.

Observed clean scans: Civis local history; 19 OmniRoute local-only commits; AgilePlus directory scan.

