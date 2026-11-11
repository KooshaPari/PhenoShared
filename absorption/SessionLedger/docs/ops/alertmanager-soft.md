# Soft Alertmanager packaging evidence (C05)

SessionLedger ships PromQL / SLO rule intent and a docs-tree Alertmanager
routing placeholder ([`alerts.md`](alerts.md),
[`alerts/alertmanager.yaml`](alerts/alertmanager.yaml)). This document covers
the **soft packaging sample**: a secrets-free Alertmanager config under
`packaging/` that proves local placeholder wiring without claiming live traffic
or production paging.

## Contract

| Knob                      | Value                                                      | Source                                                                                                   |
| ------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Packaging sample          | loopback `sessionledger-webhook-placeholder` only          | [`packaging/alertmanager/alertmanager.yml.sample`](../../packaging/alertmanager/alertmanager.yml.sample) |
| Docs-tree routing (stubs) | Slack / PagerDuty `REPLACE_ME_*` + loopback default        | [`alerts/alertmanager.yaml`](alerts/alertmanager.yaml)                                                   |
| SelfCheck                 | sample + docs anchors; no Alertmanager process; no network | [`scripts/alertmanager-soft-check.ps1`](../../scripts/alertmanager-soft-check.ps1)                       |
| Live webhook / paging IDs | **unpaid**                                                 | Operators export `SL_ALERT_*` outside the repo                                                           |

## What this proves

1. **Local placeholder** — a copy-paste Alertmanager config with a loopback
   webhook receiver and no committed secrets.
2. **Soft evidence only** — packaging presence + hermetic SelfCheck; does **not**
   start Alertmanager, scrape Prometheus, or send pages.
3. **Live webhook unpaid** — production Slack / PagerDuty / OpsGenie route IDs
   remain operator-owned (`scripts/alert-route-ids-check.ps1 -Strict`).

```text
┌────────────────────┐   soft packaging sample    ┌──────────────────────────┐
│ packaging/…sample  │───────────────────────────►│ loopback webhook only    │
│ (this evidence)    │   no secrets / no traffic  │ 127.0.0.1:9099           │
└────────────────────┘                            └──────────────────────────┘
         │
         │  unpaid ───► live Slack / PagerDuty webhooks
         ▼
┌────────────────────┐
│ docs/ops/alerts/…  │  REPLACE_ME_* stubs + route-id SoftCheck
└────────────────────┘
```

## How to run

### Self-check (hermetic; Windows-safe)

```powershell
pwsh ./scripts/alertmanager-soft-check.ps1 -SelfCheck
```

Hermetic wiring test:

```powershell
cargo test --test alertmanager_soft --locked
```

### Local Alertmanager (optional; operator machine)

```bash
# After copying the sample and starting a local sink on :9099 — not required for SelfCheck
alertmanager --config.file=packaging/alertmanager/alertmanager.yml.sample
```

## Soft Alertmanager SelfCheck

| Gate                                                | Status     |
| --------------------------------------------------- | ---------- |
| Soft Alertmanager SelfCheck                         | **done**   |
| Packaging sample (placeholder receiver, no secrets) | **done**   |
| Live webhook / production paging                    | **unpaid** |

## Related

- PromQL + routing table: [`alerts.md`](alerts.md)
- Severity stubs + game-day: [`observability.md`](observability.md#alert-stubs)
- Route ID stub SoftCheck: [`scripts/alert-route-ids-check.ps1`](../../scripts/alert-route-ids-check.ps1)

## Limitations

- Soft evidence only — does not claim Alertmanager is deployed or that pages fire.
- Packaging sample intentionally omits Slack/PagerDuty receivers (those live as
  docs stubs with `REPLACE_ME_*` tokens, never live secrets).
- Live webhook substitution and `-Strict` route-id validation remain unpaid for
  production go-live.
