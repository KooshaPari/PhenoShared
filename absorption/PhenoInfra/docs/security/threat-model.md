# Threat Model Template (STRIDE-per-component)

> **Source audit:** `FLEET-AUDIT-REPORT.md` — S7 (Threat model) is the #1 P0 gap (priority 42, 10 of 11 audited repos at score 0).
> **Method:** STRIDE per-component. Each component in your system gets a row; each STRIDE category is a column.
> **How to use:** Copy this file to your repo as `docs/security/threat-model.md`, fill in the rows, commit.

## When to do this

A threat model is **wired** (score 2) when this file exists in `docs/security/threat-model.md`
and is referenced from your `README.md` or `SECURITY.md`.
It's **measured** (score 3) when a CI gate fails if the file is more than 90 days old.

## STRIDE cheat sheet

| Letter | Threat | Property violated | Question to ask |
|--------|--------|-------------------|------------------|
| **S** | Spoofing | Authentication | Can an attacker impersonate a user/system? |
| **T** | Tampering | Integrity | Can an attacker modify data or code? |
| **R** | Repudiation | Non-repudiation | Can a user deny an action they took? |
| **I** | Information disclosure | Confidentiality | Can an attacker read data they shouldn't? |
| **D** | Denial of service | Availability | Can an attacker make the system unavailable? |
| **E** | Elevation of privilege | Authorization | Can an attacker gain higher privileges? |

For each cell, mark one of: **N/A** (not applicable to this component), **low** (impact minor,
mitigation optional), **med** (mitigation required), **high** (mitigation + test required).

---

## Component inventory

List every component in your system. A component is any discrete unit that handles data
or accepts input — a service, a CLI, a database, a queue, a third-party dependency, a
network boundary, a CI workflow, even a build artifact.

Example components (adjust to your system):
- Public web frontend
- Public API
- Auth service
- Database (primary + replicas)
- Object storage
- Message queue
- Background workers
- Admin console
- CI/CD pipeline
- Third-party LLM providers
- CLI tool
- Container runtime

## Per-component threat grid

For each component, fill in the STRIDE table.

### Component: `<name>`

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low/med/high | | | | YYYY-MM-DD |
| **T — Tampering** | | | | | |
| **R — Repudiation** | | | | | |
| **I — Info disclosure** | | | | | |
| **D — DoS** | | | | | |
| **E — Elevation** | | | | | |

Repeat this block for every component.

---

## Worked example: phenodocs

This is a real example you can copy and adapt. Below is a partial threat model for the
`phenodocs` VitePress docs site, derived from the audit.

### Component: `phenodocs` VitePress site

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low | Phishing domain mimicking phenodocs | Reserved subdomain on github.io; no custom domain | infra | 2026-06-16 |
| **T — Tampering** | med | Malicious PR that injects content via the docs build | CODEOWNERS + required PR reviews; markdownlint CI gate | docs | 2026-06-16 |
| **R — Repudiation** | low | Authorship of doc changes | Git commit signing optional; Co-Authored-By trailer required | docs | 2026-06-16 |
| **I — Info disclosure** | low | Leaked secrets in docs | trufflehog in CI; pre-commit hook | security | 2026-06-16 |
| **D — DoS** | low | GitHub Pages availability | Out of scope (GitHub-managed) | n/a | 2026-06-16 |
| **E — Elevation** | low | Branch protection bypass | CODEOWNERS gate + required status checks | docs | 2026-06-16 |

### Component: `phenodocs` CI workflows

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Compromised third-party GitHub Action | SHA-pinned all 16 workflows (verified 2026-06) | ci-ops | 2026-06-16 |
| **T — Tampering** | med | Malicious workflow change | Branch protection + CODEOWNERS | ci-ops | 2026-06-16 |
| **R — Repudiation** | low | Workflow authorship | Git log; GitHub UI history | ci-ops | 2026-06-16 |
| **I — Info disclosure** | low | Workflow logs leaking secrets | All secrets via GitHub Actions secrets (encrypted at rest) | security | 2026-06-16 |
| **D — DoS** | low | Workflow abuse / quota exhaustion | Concurrency groups on all workflows; standard runners only | infra | 2026-06-16 |
| **E — Elevation** | med | Workflow gains write access via compromised PAT | `permissions: contents: read` on all 16 workflows | ci-ops | 2026-06-16 |

---

## How to lift the S7 score

- **0 → 1 (ad-hoc):** Add a `docs/security/threat-model.md` with at least one component's STRIDE table.
- **1 → 2 (wired):** Reference the threat model from `README.md` and `SECURITY.md`. Cover at least 80% of your components. Add an owner + last-reviewed column to each row.
- **2 → 3 (measured):** Add a CI gate that fails if `docs/security/threat-model.md` is older than 90 days, OR if a previously-scored component row is deleted.

## Review cadence

Review the threat model:
- **On every major release** (semver minor)
- **On any new external dependency** added
- **On any new public-facing endpoint**
- **Quarterly minimum** (a 90-day-old model is a CI failure for "measured" repos)

## Cross-references

- `BACKLOG.md` — the P0 list; S7 is the #1 item.
- `FLEET-AUDIT-REPORT.md` — the per-pillar fleet-wide distribution.
- Per-repo `ACTION-PLAN.md` files — each has a "Build" phase with S7 task entries.

## How to validate

```bash
# After writing your threat model, validate it has all 5 STRIDE rows
for c in S T R I D E; do
  grep -q "^\*\*$c " docs/security/threat-model.md || echo "missing $c"
done
```

If `grep` returns nothing for all 6 letters, your file is valid.

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (S7 P0)
- **License:** Same as the parent repo
