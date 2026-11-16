---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
date: 2026-06-05
owner: repo-steward
plan_status: NOT_STARTED
retirement_criteria: Every active <REDACTED> service emits structured logs, OpenTelemetry metrics, and traces; a unified dashboard exists; coverage report is 100% for active services.
slug: eco-031-observability-baseline
spec_id: eco-031
state: PENDING
status: active
superseded_by: null
title: Observability Baseline
type: operational
---
# Observability Baseline

## Problem
<REDACTED> services emit logs in inconsistent formats (plain text, JSON, mixed) and have no standardized metrics or traces. When a user reports an issue, the team cannot correlate logs to performance data or reconstruct a request flow. There is no single dashboard that surfaces the health of the ecosystem.

## Target Users
Repo stewards, on-call operators, spec authors, downstream consumers, and end users reporting issues.

## Functional Requirements
1. Every user-facing service emits structured logs (JSON, RFC 3339 timestamps, stable field names: `level`, `msg`, `service`, `trace_id`, `span_id`).
2. Every user-facing service exposes OpenTelemetry metrics (RED metrics: rate, errors, duration) over OTLP.
3. Every user-facing service emits OpenTelemetry traces with W3C `traceparent` propagation.
4. A unified observability dashboard exists (Grafana or equivalent) with per-service RED panels and a fleet-level overview.
5. Coverage is reported per service in `worklogs/observability-coverage-<date>.json` with `{service, logs: bool, metrics: bool, traces: bool, last_emitted_at}`.
6. A linter (eco-031-lint) fails any service that is active but missing one of the three signals.

## Non-Functional Requirements
- Log emission overhead < 1% of request latency at p99
- UTF-8 no BOM
- Idempotent report generation
- OpenTelemetry SDK version pinned in a shared governance doc

## Acceptance Criteria
- Observability coverage = 100% for active services (every active service has logs + metrics + traces = true)
- Dashboard URL is published in `docs/operations/observability.md`
- Coverage report lists every active service with a timestamp
- Removing instrumentation from any service breaks `make observability-check`

## Constraints
- Depends on eco-006 governance-sync (coverage must be tracked)
- Depends on eco-018 spec-first (this spec must be referenced by the linter)
- Depends on eco-026 autograder (`make observability-check` is a gate)
- Active service list is the output of `agileplus repo list --active`
