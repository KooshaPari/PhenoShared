# Alert queries — SessionLedger (C05)

**Status:** PromQL examples and routing evidence for shipped RED metrics.
Alertmanager paging is **not** enabled by this repository — operators replace
the webhook placeholder in [`alerts/alertmanager.yaml`](alerts/alertmanager.yaml)
before production use. Soft packaging sample (loopback placeholder, no secrets):
[`alertmanager.yml.sample`](../../packaging/alertmanager/alertmanager.yml.sample)
— see [`alertmanager-soft.md`](alertmanager-soft.md).

Canonical severity + promotion table:
[`observability.md`](observability.md#alert-stubs). Operator triage:
[`runbook.md`](runbook.md). Game-day cadence:
[`observability.md`](observability.md#game-day-cadence).

## PromQL for shipped RED metrics

The daemon exports aggregate HTTP RED counters at `/metrics` on every scrape.
After traffic, Wave-19 also emits per-route `route` labels and histogram
`_bucket` series (see [`dashboards/README.md`](dashboards/README.md)). Prometheus
adds `job="sl-daemon"` at scrape time — include that label in deployed queries.

These aggregate queries work even when no per-route series exist yet. They use
`rate`, which safely handles counter resets.

| Signal                   | PromQL                                                                                                                                                           |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Request rate (completed) | `sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[5m]))`                                                                                         |
| Error rate               | `sum(rate(sl_http_errors_total{job="sl-daemon"}[5m]))`                                                                                                           |
| Error ratio              | `sum(rate(sl_http_errors_total{job="sl-daemon"}[5m])) / clamp_min(sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[5m])), 1e-9)`                 |
| Mean duration            | `sum(rate(sl_http_request_duration_seconds_sum{job="sl-daemon"}[5m])) / clamp_min(sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[5m])), 1e-9)` |
| Started requests         | `sum(rate(sl_http_requests_total{job="sl-daemon"}[5m]))`                                                                                                         |
| Scrape up                | `max(up{job="sl-daemon"})`                                                                                                                                       |
| RED series present       | `count(sl_http_requests_total{job="sl-daemon"})`                                                                                                                 |

`sl_http_requests_total` increments when a request starts, while
`sl_http_request_duration_seconds_count` increments when it completes. Use the
completed count as the denominator for both error ratio and mean duration.

### Per-route queries (after traffic)

Per-route series appear only after requests hit labeled paths. Use these in
Grafana or game-day PromQL drills once load smoke has run:

| Signal             | PromQL                                                                                                                                                                                       |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route request rate | `sum by (route) (rate(sl_http_requests_total{job="sl-daemon",route!=""}[5m]))`                                                                                                               |
| Route error ratio  | `sum by (route) (rate(sl_http_errors_total{job="sl-daemon",route!=""}[5m])) / clamp_min(sum by (route) (rate(sl_http_request_duration_seconds_count{job="sl-daemon",route!=""}[5m])), 1e-9)` |
| Route p95 latency  | `histogram_quantile(0.95, sum by (route, le) (rate(sl_http_request_duration_seconds_bucket{job="sl-daemon",route!=""}[5m])))`                                                                |

Aggregate `_sum` / `_count` without `route` remain valid for service-wide SLO
alerts. Do **not** run `histogram_quantile` on the unlabeled aggregate summary
lines — only on `route`-labeled `_bucket` series.

## Alert routing evidence

Maps promoted alerts to runnable PromQL, Alertmanager intent, and load status.
Replace webhook URL and receiver names before paging.

| Alert                              | PromQL / expr (runnable)                                       | `severity` label      | Intended route                            | Loaded                                                    |
| ---------------------------------- | -------------------------------------------------------------- | --------------------- | ----------------------------------------- | --------------------------------------------------------- |
| `SessionLedgerDaemonScrapeDown`    | `up{job="sl-daemon"} == 0`                                     | `warning` (P1 intent) | PagerDuty / on-call (TBD) via placeholder | [`sessionledger-slo.yaml`](alerts/sessionledger-slo.yaml) |
| `SessionLedgerDaemonScrapeMissing` | `absent(up{job="sl-daemon"})`                                  | `warning`             | Slack `#sessionledger-ops` (TBD)          | `sessionledger-slo.yaml`                                  |
| `SessionLedgerFastErrorBudgetBurn` | error ratio &gt; 5% over 5m (see rule file)                    | `warning`             | Slack `#sessionledger-ops` (TBD)          | `sessionledger-slo.yaml`                                  |
| `SessionLedgerSlowErrorBudgetBurn` | error ratio &gt; 1% over 1h                                    | `info`                | friction-log only                         | `sessionledger-slo.yaml`                                  |
| `SessionLedgerHighMeanLatency`     | mean latency &gt; 1s over 10m                                  | `info`                | friction-log                              | `sessionledger-slo.yaml`                                  |
| `SessionLedgerRedMetricsMissing`   | `up == 1 unless sl_http_requests_total`                        | `warning`             | Slack (TBD)                               | `sessionledger-slo.yaml`                                  |
| `SL-METRICS-STALE`                 | `max(up{job="sl-daemon"}) == 0 or absent(up{job="sl-daemon"})` | `info`                | Slack (TBD)                               | docs (overlaps scrape-down)                               |

Alertmanager config ([`alertmanager.yaml`](alerts/alertmanager.yaml)):

```yaml
route:
  receiver: sessionledger-webhook-placeholder
  routes:
    - receiver: sessionledger-pagerduty # severity=warning + page=true
    - receiver: sessionledger-slack-ops # severity=warning
    - receiver: sessionledger-webhook-placeholder
```

Production mapping (stubs checked in; live IDs via env — never commit secrets):

| `severity` / intent          | Receiver                            | Route ID stub / env                                                   |
| ---------------------------- | ----------------------------------- | --------------------------------------------------------------------- |
| `warning` + `page=true` (P1) | `sessionledger-pagerduty`           | `SL_ALERT_PAGERDUTY_ROUTING_KEY` ← `REPLACE_ME_PAGERDUTY_ROUTING_KEY` |
| `warning` (P2)               | `sessionledger-slack-ops`           | `SL_ALERT_SLACK_CHANNEL_ID` + `SL_ALERT_SLACK_WEBHOOK_URL`            |
| default / `info`             | `sessionledger-webhook-placeholder` | loopback webhook (local only)                                         |

Stub env file: [`route-ids.stub.env`](alerts/route-ids.stub.env). Soft validation
always accepts placeholders; `-Strict` requires live env:

```powershell
pwsh -NoProfile -File scripts/alert-route-ids-check.ps1
pwsh -NoProfile -File scripts/alert-route-ids-check.ps1 -Strict
```

Validate Prometheus rules locally:

```bash
promtool check rules docs/ops/alerts/sessionledger-slo.yaml
```

## Rules using shipped metrics

These examples can be placed under a Prometheus rule group's `rules` array.
Tune thresholds and `for` durations against observed traffic before paging.

### `SL-HTTP-HIGH-ERROR-RATIO` (P2) — alias of fast burn

Same expression as `SessionLedgerFastErrorBudgetBurn` in
[`sessionledger-slo.yaml`](alerts/sessionledger-slo.yaml).

```yaml
alert: SL-HTTP-HIGH-ERROR-RATIO
expr: |
  (
    sum(rate(sl_http_errors_total{job="sl-daemon"}[15m]))
      /
    clamp_min(
      sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[15m])),
      1e-9
    )
  ) > 0.05
  and
  sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[15m])) > 0
for: 15m
labels:
  severity: ticket
  job: sl-daemon
annotations:
  summary: "sl-daemon HTTP error ratio exceeded 5%"
  runbook: docs/ops/runbook.md#common-failures
```

### `SL-HTTP-HIGH-MEAN-LATENCY` (P3)

```yaml
alert: SL-HTTP-HIGH-MEAN-LATENCY
expr: |
  (
    sum(rate(sl_http_request_duration_seconds_sum{job="sl-daemon"}[15m]))
      /
    clamp_min(
      sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[15m])),
      1e-9
    )
  ) > 1
  and
  sum(rate(sl_http_request_duration_seconds_count{job="sl-daemon"}[15m])) > 0
for: 15m
labels:
  severity: info
  job: sl-daemon
annotations:
  summary: "sl-daemon mean HTTP latency exceeded 1 second"
  runbook: docs/ops/runbook.md#common-failures
```

### `SL-RED-METRICS-MISSING` (P2)

Distinguishes a reachable scrape target from an exporter that no longer
publishes the expected application series.

```yaml
alert: SL-RED-METRICS-MISSING
expr: |
  up{job="sl-daemon"} == 1
  unless
  sl_http_requests_total{job="sl-daemon"}
for: 5m
labels:
  severity: ticket
  job: sl-daemon
annotations:
  summary: "sl-daemon scrape succeeds but RED metrics are missing"
  runbook: docs/ops/runbook.md#metrics
```

### `SL-METRICS-STALE` (P3) — promoted via scrape `up`

```yaml
alert: SL-METRICS-STALE
expr: |
  max(up{job="sl-daemon"}) == 0
  or
  absent(up{job="sl-daemon"})
for: 5m
labels:
  severity: info
  job: sl-daemon
annotations:
  summary: "Prometheus cannot scrape sl-daemon /metrics"
  runbook: docs/ops/runbook.md#metrics
```

## Future-signal rule sketches

Do **not** load until the listed metrics exist.

### `SL-HEALTHZ-DOWN` (P1)

Use `SessionLedgerDaemonScrapeDown` today. Blackbox probe variant:

```yaml
# STUB — requires probe_success{path="/healthz"}
alert: SL-HEALTHZ-DOWN
expr: up{job="sl-daemon"} == 0 or probe_success{path="/healthz"} == 0
for: 1m
labels:
  severity: page
annotations:
  summary: "sl-daemon liveness failed"
  runbook: docs/ops/runbook.md#health-check
```

### `SL-READYZ-DOWN` (P2)

Manual evidence: [`ops-chaos-smoke.ps1`](../../scripts/ops-chaos-smoke.ps1) phase 1
and game-day JSON `readiness_fault` step.

```yaml
# STUB — requires probe_success{path="/readyz"}
alert: SL-READYZ-DOWN
expr: probe_success{path="/readyz"} == 0 and probe_success{path="/healthz"} == 1
for: 2m
labels:
  severity: ticket
annotations:
  summary: "sl-daemon alive but not ready (check out_dir / SL_DATA_DIR)"
  runbook: docs/ops/runbook.md#health-check
```

### `SL-INGEST-ERROR-BUDGET` (P2)

```yaml
# STUB — requires endpoint-specific ingest counters (not the aggregate HTTP counters)
alert: SL-INGEST-ERROR-BUDGET
expr: |
  rate(sl_ingest_errors_total[15m])
    / rate(sl_ingest_requests_total[15m]) > 0.05
for: 15m
labels:
  severity: ticket
annotations:
  summary: "ingest error rate exceeded 5% SLO stub"
  runbook: docs/ops/observability.md#slo-stubs-intentional-placeholders
```

### `SL-REPLAY-LATENCY` (P3)

```yaml
# STUB — requires future histogram sl_replay_ttfb_seconds
alert: SL-REPLAY-LATENCY
expr: histogram_quantile(0.95, rate(sl_replay_ttfb_seconds_bucket[30m])) > 2
for: 30m
labels:
  severity: info
annotations:
  summary: "replay TTFB p95 above 2s fixture SLO stub"
```

## Promotion checklist

1. Import the RED dashboard and validate aggregate + route queries against each
   deployed replica.
2. Tune aggregate error-ratio and mean-latency thresholds from production
   baselines.
3. Run quarterly game-day workflow; archive `gameday-evidence.json`.
4. Add route-labelled ingest/replay counters before enabling their alert stubs.
5. Replace `probe_*` stubs with real blackbox metrics.
6. Export live `SL_ALERT_*` values (never commit), substitute into
   [`alertmanager.yaml`](alerts/alertmanager.yaml), and pass
   `scripts/alert-route-ids-check.ps1 -Strict`.
7. Close remaining #65 exporter items; keep these files as the source of truth
   for rule intent.
