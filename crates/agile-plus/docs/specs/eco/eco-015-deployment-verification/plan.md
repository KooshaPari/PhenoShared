# Deployment Verification — Plan

## Objective

Establish a deterministic, machine-verified check that every repo flagged as deployable by `eco-009` actually has a live URL and a recent `last_deploy` timestamp, and surface the result as a single dated JSON plus a worklog pointer.

## Scope

- **In:** Local Rust binary (or 5-line Bash glue with inline justification) that walks the repos index, reads `docs/deployment.md`, probes each URL, classifies state, and emits `worklogs/deploy-status-<date>.json`. Worklog wiring only; no doc rewrites.
- **Out:** Auto-remediation of broken deploys, CI integration, alerting, mutation of `docs/deployment.md`. Authentication-gated URLs are out-of-scope (treated as `unknown` with a reason).

## Implementation Steps

1. **Discovery (DAG: none)**
   - Reuse the deployable-repo list produced by `eco-009` (`worklogs/DEPLOYMENT.md` index).
   - Confirm each candidate has `docs/deployment.md` with a parseable URL and `last_deploy` field.
2. **Probe (DAG: → 1)**
   - For each candidate, HTTP GET the URL with a 30s timeout.
   - Capture status code, response time, redirect target.
3. **Classify (DAG: → 2)**
   - Apply FR-2..FR-5: `live | stale | broken | unknown`.
   - Record skipped repos (FR-6) with reasons.
4. **Emit (DAG: → 3)**
   - Write `worklogs/deploy-status-<YYYY-MM-DD>.json` atomically.
   - Append a pointer line to `worklogs/DEPLOYMENT.md` (idempotent overwrite per AC-4).
5. **Triage (DAG: → 4)**
   - For every `broken` / `unknown`, append an `INTEGRATION.md` entry with owner, repo, URL, failure mode.
6. **Verify (DAG: → 5)**
   - Confirm AC-1..AC-4 hold; capture sample run in `worklogs/DEPLOYMENT.md` history.
