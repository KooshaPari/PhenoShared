# Data Retention Policy Template

> **Source audit:** `FLEET-AUDIT-REPORT.md` — PR2 (Data retention) is P1 priority (10/11 audited repos at score 0).
> **Method:** Add `docs/security/retention.md` documenting the retention policy for each data category the repo handles.
> **How to use:** Copy this file to your repo as `docs/security/retention.md`, customize the table, commit, push. Lifts PR2 from 0 to 2 (wired).

## What is PR2?

PR2 (Data retention) = the repo has a documented policy for how long each category of data is retained, when it's deleted, and who has access. The policy covers PII, logs, build artifacts, user-generated content, and backups.

**The "wired" (PR2=2) signal**: `docs/security/retention.md` exists with a per-data-category table; the policy is referenced from `README.md` and `SECURITY.md`; the table is reviewed at least annually.

## Template: `docs/security/retention.md`

```markdown
# Data Retention Policy

> **Last reviewed:** 2026-06-17
> **Owner:** @<handle>
> **Review cadence:** Annual (next review 2027-06-17)

## Scope

This document covers all data categories handled by this repo: source code, build artifacts, user-generated content, logs, backups, and any PII.

## Retention table

| Data category | Storage location | Retention period | Deletion method | Access control | PII? |
|---------------|------------------|------------------|------------------|----------------|------|
| Source code | GitHub repo | Indefinite (or "until repo archived") | Repo archival | Public (or per repo settings) | No |
| Build artifacts | GitHub Actions artifacts | 90 days | Auto-purged by GitHub | Repo maintainers | No |
| Release artifacts (binaries, SBOMs) | GitHub Releases | Indefinite | Manual (or "until repo archived") | Public | No |
| CI logs | GitHub Actions logs | 90 days | Auto-purged by GitHub | Repo maintainers | No |
| Issue tracker | GitHub Issues | Indefinite | Manual | Public (or per repo settings) | Optional (user may post PII) |
| Pull request comments | GitHub PRs | Indefinite | Manual | Public (or per repo settings) | Optional |
| User accounts | GitHub user database | Indefinite (until user deletes) | User-initiated | User | Yes (email) |
| Telemetry / metrics | (if any, list here) | 30 days | Auto-purged | Maintainers | Depends |
| Logs (production) | (if any, list here) | 30 days | Auto-purged | Maintainers | Depends |
| Backups | (if any, list here) | 1 year | Manual rotation | Maintainers | Depends |

## Procedures

### Review

- **When:** Annual (or on any new data category added)
- **Who:** Repo owner + security lead
- **What:** Confirm each data category still matches the table; update retention period if policy changed

### Deletion

- **Data subject deletion request:** Within 30 days of request, delete all data subject's records from primary + backup storage. Document the deletion in `docs/security/retention-log.md`.
- **End-of-retention deletion:** Run the deletion script (if any) or manually delete the data. Document the deletion in `docs/security/retention-log.md`.

### Breach

- **Data breach:** Within 72 hours, notify affected users + the security lead. Document the breach + response in `docs/security/breach-log.md`.

## Compliance

- **GDPR:** If you process EU personal data, you have a 72-hour breach notification obligation.
- **CCPA:** If you process California personal data, you have a data subject access + deletion obligation.
- **HIPAA:** If you process health data, you have additional BAA + audit log obligations.

## Cross-references

- `SECURITY.md` — vulnerability disclosure policy
- `docs/security/threat-model.md` — what data is at risk
- `docs/operations/slos.md` — when retention violations trigger alerts

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (PR2 P1)
- **License:** Same as the parent repo
```

## How to apply

1. Copy the template above to your repo as `docs/security/retention.md`.
2. Customize the table to match your repo's actual data categories (add/remove rows).
3. Update the "Owner" and "Last reviewed" fields.
4. Reference from `README.md` and `SECURITY.md` (add 1 line each).
5. Commit + push + open a PR.

## PR2 score lift

- **0 → 1 (ad-hoc):** file exists but not referenced from anywhere.
- **0 → 2 (wired):** file exists AND is referenced from `README.md` and `SECURITY.md` AND the table covers all major data categories.
- **0 → 3 (measured):** a CI gate fails if `docs/security/retention.md` is older than 365 days (annual review enforced).

## Reference: OmniRoute

OmniRoute is the reference repo for PR2 (PR2=1, partial). It has a retention policy in its docs but no CI gate. The template above extends that pattern with a CI-enforceable review cadence.

## How to validate

After applying:
1. `grep -r "retention" docs/` — should find the new file
2. `grep "retention" README.md SECURITY.md` — should find references in both
3. The table has at least 5 rows (source code, build artifacts, issues, user data, backups)

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (PR2 P1)
- **Reference repo:** `KooshaPari/OmniRoute` (PR2=1)
- **License:** Same as the parent repo
