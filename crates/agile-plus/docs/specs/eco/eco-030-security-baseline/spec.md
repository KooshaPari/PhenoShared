---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
last_audit: 2026-06-05
plan_status: REQUIRED
slug: eco-030-security-baseline
spec_id: eco-030
state: PENDING
status: active
superseded_by: null
title: Security Baseline
type: operational
---
# Specification: Security Baseline

## Problem Statement
The 9-clone audit (`worklogs/clone-fill-audit-20260605.json`) shows 8/9 repos lack `LICENSE`. The fleet has no consistent security policy per repo. Vulnerability reporting, dep audit, secret scan, and code ownership are not standardized.

## Target Users
- **Repo stewards** onboarding new repos.
- **Security reviewers** triaging CVE notifications.
- **External reporters** who need a clear `SECURITY.md` policy.

## Functional Requirements
- **FR-1**: Every active repo MUST have a `SECURITY.md` referencing the Phenotype Org `security.txt` and a `private-vuln-reporting@phenotype.local` mailbox.
- **FR-2**: Every active repo MUST have `LICENSE` (MIT preferred; Apache-2.0 acceptable for non-<REDACTED> code).
- **FR-3**: Every active repo MUST have a `.github/CODEOWNERS` mapping critical paths to owners.
- **FR-4**: CI MUST run `cargo audit` (or `npm audit` / `pip-audit` / `govulncheck` as appropriate) on every PR.
- **FR-5**: A pre-commit hook MUST run trufflehog secret-scan on staged files.
- **FR-6**: A `make security-audit` target MUST aggregate all of the above and exit non-zero on any failure.

## Acceptance Criteria
- `make security-audit` exits 0 on the live tree.
- Every active repo has SECURITY.md, LICENSE, and CODEOWNERS.
- A test PR that introduces a hard-coded secret is blocked.

## Constraints & Dependencies
- Depends on eco-024 (traceability) — every gap is an FR.
- Depends on eco-021 (BDD/SDD/TDD/XDD gates) — security test is a test.
- Depends on eco-011 (action-hygiene) — supply-chain pinning.
