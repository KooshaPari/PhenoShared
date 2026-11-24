---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
slug: eco-015-deployment-verification
spec_id: eco-015
state: PENDING
status: active
superseded_by: null
title: Deployment Verification
type: operational
---
# Deployment Verification

## Problem

`eco-009-deploy-markers` requires every deployable repo to carry `docs/deployment.md` with a live URL and last-deploy timestamp. The marker exists, but no automated check verifies that the URL actually resolves or that the recorded timestamp reflects a real, recent deployment. A stale or broken deploy marker is indistinguishable from a healthy one in the current ecosystem.

## Target Users

- Repo stewards confirming their app or docs site is genuinely live.
- Operators running cross-repo health sweeps who need a machine-verifiable deploy signal.
- Downstream agents and dashboards consuming deploy state to gate merges or pages.

## Functional Requirements

- **FR-1:** For every repo flagged as deployable (carries `docs/deployment.md`), emit `worklogs/deploy-status-<YYYY-MM-DD>.json` with shape `{repo, url, last_deploy, status}` where `status` is one of `live | stale | broken | unknown`.
- **FR-2:** `live` requires the URL to return HTTP 2xx within 30s and `last_deploy` to be within 7 days of run date.
- **FR-3:** `stale` is `last_deploy` older than 7 days, URL still 2xx.
- **FR-4:** `broken` is URL non-2xx, timeout, or DNS failure.
- **FR-5:** `unknown` reserved for cases where the marker exists but URL or timestamp is missing/malformed; treated as failure for ACs.
- **FR-6:** Skip cases (no `docs/deployment.md`, or repo marked non-deployable) MUST be enumerated in the same JSON under a `skipped` array with `{repo, reason}`.

## Acceptance Criteria

- AC-1: Verification reaches N/N of deployable repos OR each skip is documented with a reason.
- AC-2: `deploy-status-<date>.json` is parsable, schema-stable, and indexed in `worklogs/DEPLOYMENT.md`.
- AC-3: Any `broken` or `unknown` repo triggers a follow-up worklog entry under `worklogs/INTEGRATION.md` with a remediation owner.
- AC-4: Re-run on the same day is idempotent and overwrites the prior `<date>.json` only when content changes.

## Constraints

- Read-only network probes; no auth credentials stored.
- Runs locally; no CI dependency (billing-blocked).
- Disk-full aware: writes only the dated JSON plus a worklog pointer; no clones.
- 30s hard timeout per URL probe to keep the sweep bounded.
