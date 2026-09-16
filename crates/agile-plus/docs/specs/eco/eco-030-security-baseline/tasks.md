# Tasks: Security Baseline

## WP-01: Templates
**Effort:** S
- [ ] T001 — SECURITY.md template.
- [ ] T002 — LICENSE template (MIT).
- [ ] T003 — CODEOWNERS template.

## WP-02: Per-repo fan-out
**Effort:** M
- [ ] T004 — Apply to the 8 cloned <REDACTED> repos (eco-025) that lack LICENSE.
- [ ] T005 — Apply to all active repos that lack SECURITY.md (backfill pass).

## WP-03: CI gates
**Effort:** M
- [ ] T006 — `cargo audit` workflow template.
- [ ] T007 — `npm audit` workflow template.
- [ ] T008 — `pip-audit` workflow template.
- [ ] T009 — `govulncheck` workflow template.
- [ ] T010 — trufflehog pre-commit hook.

## WP-04: Aggregate
**Effort:** S
- [ ] T011 — `make security-audit` target at the AgilePlus root.
- [ ] T012 — Wire into autograder (eco-026).
