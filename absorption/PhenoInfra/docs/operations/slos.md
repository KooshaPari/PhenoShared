# SLO (Service Level Objectives) Template

> **Source audit:** `FLEET-AUDIT-REPORT.md` — OB4 (SLOs) is P1 priority (10/11 audited repos at score 0).
> **Method:** Add `docs/operations/slos.md` documenting the SLOs (availability, latency, error rate, throughput) for each service the repo provides.
> **How to use:** Copy this file to your repo as `docs/operations/slos.md`, customize the table, commit, push. Lifts OB4 from 0 to 2 (wired).

## What is OB4?

OB4 (SLOs) = a documented set of Service Level Objectives with measurable targets. The SLOs cover availability, latency, error rate, and throughput. Each SLO has a current measurement (e.g., rolling 30-day availability) and a burn rate (e.g., how much of the error budget is consumed).

**The "wired" (OB4=2) signal**: `docs/operations/slos.md` exists with per-service SLOs + targets + measurement methodology. The SLOs are referenced from `README.md`.

## Template: `docs/operations/slos.md`

```markdown
# Service Level Objectives (SLOs)

> **Last reviewed:** 2026-06-17
> **Owner:** @<handle>
> **Review cadence:** Quarterly (next review 2026-09-15)

## Scope

This document covers the SLOs for all services this repo provides. For libraries/CLIs, "service" means the package's API surface; for web apps, it's the HTTP endpoints.

## SLO table

| Service | SLI | Target | Measurement window | Current (30d) | Error budget | Burn rate alert |
|---------|-----|--------|-------------------|----------------|--------------|-----------------|
| `<service 1>` (e.g., `POST /api/v1/foo`) | Availability | 99.9% (≤ 8.7h downtime/year) | 30 days rolling | 99.95% | 8.7h/year | Page on 2x burn over 1h |
| `<service 1>` (e.g., `POST /api/v1/foo`) | Latency p99 | ≤ 200ms | 30 days rolling | 180ms | n/a | Page on p99 > 400ms for 5min |
| `<service 1>` (e.g., `POST /api/v1/foo`) | Error rate | ≤ 0.1% (5xx) | 30 days rolling | 0.05% | n/a | Page on 5xx > 1% for 5min |
| `<service 2>` (e.g., `CLI binary`) | Build success | 99% | 30 days rolling | 99.2% | n/a | Page on 3 consecutive failures |
| (add rows for each service) | | | | | | |

## SLI methodology

### Availability
- **Definition:** `(successful_requests / total_requests) * 100`
- **Source:** Prometheus / Datadog / Cloud provider metrics
- **Excludes:** Health check pings, intentional maintenance windows

### Latency
- **Definition:** p50, p95, p99 latency in milliseconds
- **Source:** APM (Datadog, OpenTelemetry, Jaeger)
- **Excludes:** Cold-start latency, network retries

### Error rate
- **Definition:** `(5xx_responses / total_responses) * 100`
- **Source:** Application logs / metrics
- **Excludes:** 4xx client errors, intentional 503 during deploys

## Error budget policy

- **Budget reset:** Calendar quarter (Jan 1, Apr 1, Jul 1, Oct 1)
- **Burn rate alerts:** Page on 2x burn (consuming budget at 2x the steady-state rate) over any 1-hour window
- **Budget freeze:** When the budget is exhausted, all non-critical deploys are frozen until the next quarter

## Procedures

### Review

- **When:** Quarterly
- **Who:** Service owner + SRE
- **What:** Confirm SLOs still match user expectations; adjust targets if they were too aggressive or too lax; add SLOs for any new service

### Incident response

- **When:** SLO burn rate alert fires
- **Who:** On-call SRE
- **What:** Acknowledge the page, investigate the burn rate, mitigate the cause, write a post-mortem

### Post-mortem

- **When:** Any SLO violation that consumed > 10% of the quarterly budget
- **Who:** Service owner + SRE
- **What:** Document the incident, root cause, mitigation, and action items in `docs/operations/post-mortems/<date>-<slug>.md`

## Cross-references

- `docs/security/threat-model.md` — what threats affect the SLOs
- `docs/security/retention.md` — how long to retain the SLI measurement data
- `docs/operations/runbooks.md` — how to respond to specific SLO violations

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (OB4 P1)
- **License:** Same as the parent repo
```

## How to apply

1. Copy the template above to your repo as `docs/operations/slos.md`.
2. Customize the table to match your repo's actual services.
3. Update the "Owner" and "Last reviewed" fields.
4. Reference from `README.md` (1 line under "Operations" or "Documentation" section).
5. Commit + push + open a PR.

## OB4 score lift

- **0 → 1 (ad-hoc):** file exists but not referenced.
- **0 → 2 (wired):** file exists AND is referenced from `README.md` AND the table covers all major services.
- **0 → 3 (measured):** a CI gate fails if `docs/operations/slos.md` is older than 90 days (quarterly review enforced) OR if the SLO is violated (alerting wired).

## Reference: OmniRoute

OmniRoute is the reference repo for OB4 (OB4=2). It has SLOs in its docs and a public status page. The template above is a minimal extraction of that pattern.

## How to validate

After applying:
1. `grep -r "slos\|SLO" docs/` — should find the new file
2. `grep "slos\|SLO" README.md` — should find a reference
3. The table has at least 3 rows (one per SLI category: availability, latency, error rate)

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (OB4 P1)
- **Reference repo:** `KooshaPari/OmniRoute` (OB4=2)
- **License:** Same as the parent repo
