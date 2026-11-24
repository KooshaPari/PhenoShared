# Plan: Security Baseline

## Objective
A fleet where every active repo has SECURITY.md, LICENSE, CODEOWNERS, and a CI gate that audits deps + secrets.

## Scope
- All 117 Phenotype / <REDACTED> repos.

## Implementation Steps
1. Author `AgilePlus/security-template/SECURITY.md`, `LICENSE`, `CODEOWNERS` templates.
2. Per-repo fan-out: copy templates via fresh worktrees (eco-019).
3. Wire `cargo audit` / `npm audit` / `pip-audit` / `govulncheck` to per-repo CI.
4. Wire trufflehog pre-commit hook.
5. Aggregate into `make security-audit`.

## Verification
- `make security-audit` exits 0.
- A test secret `AKIA...` in a PR is blocked.
