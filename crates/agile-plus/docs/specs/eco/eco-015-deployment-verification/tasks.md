# Deployment Verification — Tasks

## WP-01: Discovery
- Read `worklogs/DEPLOYMENT.md` (eco-009 output) to enumerate deployable repos.
- Validate each entry has a parseable URL and `last_deploy` field in `docs/deployment.md`.
- Output: in-memory list `[{repo, url, last_deploy}]` plus a `skipped` list with reasons.

## WP-02: Probe & Classify
- HTTP GET each URL with a 30s timeout (no auth, read-only).
- Map results to `live | stale | broken | unknown` per FR-2..FR-5.
- Tag stale (>7d) and broken (non-2xx / timeout / DNS) explicitly.

## WP-03: Emit & Index
- Write `worklogs/deploy-status-<YYYY-MM-DD>.json` atomically with shape `{repo, url, last_deploy, status}` plus `skipped: [{repo, reason}]`.
- Append a pointer line to `worklogs/DEPLOYMENT.md` (idempotent overwrite per AC-4).

## WP-04: Triage & Verify
- For every `broken` / `unknown` repo, append a remediation entry to `worklogs/INTEGRATION.md` with owner, URL, failure mode.
- Run a second pass to confirm AC-1..AC-4 (N/N coverage, JSON parsable, idempotency, worklog linkage).
