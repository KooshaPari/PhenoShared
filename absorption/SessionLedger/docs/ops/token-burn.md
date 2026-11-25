# Token-Burn Ledger Smoke (L78 evidence)

SessionLedger tracks coarse token estimates on continuation bundles and exposes
aggregated token stats on `GET /api/metrics`. Harbor-tied per-eval cost ledgers
remain **N/A** (see [`EVAL_SCOPE.md`](../EVAL_SCOPE.md)); this smoke instead
records a **per-fixture planning ledger** on the compression/token OKF family.

## What is checked

For each fixture listed in [`token-burn.json`](token-burn.json):

1. **Intent ledger** — every `intent` entity with `properties.token_estimate` is
   collected and summed.
2. **Gate total** — the `gate` entity `properties.total_token_estimate` must
   equal that intent sum and match the pinned config row.
3. **Compression-only baseline** — `auth-fix-session-001` participates in the zstd
   gate but carries no intent token ledger.
4. **Metrics surface docs** — `total_tokens`, `avg_tokens`, Harbor N/A, and
   `token-burn-check.ps1` anchors stay present in this doc and the watched files
   (`crates/sl-daemon/src/metrics.rs`, [`observability.md`](observability.md),
   [`openapi.yaml`](../api/openapi.yaml)).

The Rust companion test in `tests/compression_eval.rs` re-validates the same
intent→gate sums inside the `compress` feature gate.

## How to run

### Self-check (hermetic; CI default)

```powershell
pwsh ./scripts/token-burn-check.ps1 -SelfCheck
```

### Self-check + compression eval

```powershell
pwsh ./scripts/token-burn-check.ps1 -SelfCheck -RunEval
```

Or run the eval directly (see [`eval-compression.md`](eval-compression.md)):

```sh
cargo test -p session-ledger --features compress --test compression_eval --locked
```

## Fixture ledger (pinned)

| Fixture                                    | Intent token estimates | Gate `total_token_estimate` |
| ------------------------------------------ | ---------------------: | --------------------------: |
| `task-family-token-budget-032.okf.json`    |              210 + 160 |                         370 |
| `task-family-compress-resume-033.okf.json` |              240 + 120 |                         360 |
| `compress-token-proxy-034.okf.json`        |               180 + 90 |                         270 |
| `token-slice-budget-035.okf.json`          |              160 + 120 |                         280 |
| `archive-gzip-resume-036.okf.json`         |              200 + 110 |                         310 |
| `auth-fix-session-001.okf.json`            |   _(compression only)_ |                           — |

Update [`token-burn.json`](token-burn.json) and this table together when fixture
token fields change.

## Ops metrics vs eval ledgers

| Surface                                                      | Purpose                           | Harbor tie-in      |
| ------------------------------------------------------------ | --------------------------------- | ------------------ |
| `ContinuationBundle.token_estimate` / `total_token_estimate` | Planning proxy for inject slices  | **N/A**            |
| `GET /api/metrics` → `total_tokens`, `avg_tokens`            | Operator session aggregates       | **N/A**            |
| `compression_eval` bytes_saved / 4 proxy                     | Coarse compression savings signal | **N/A**            |
| Harbor per-eval / per-route token-burn ledger                | Agent-eval cost accounting        | **N/A** (deferred) |

These ledgers are intentionally shallow evidence: they catch wiring regressions
and document the boundary between ops metrics and eval-cost accounting.
