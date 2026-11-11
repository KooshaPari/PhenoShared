# Daemon-graph hard (C00 L7 live tokio ports)

Status: **C00 L7** — ports the production `sl-daemon` watcher → mpsc →
broadcast → SSE subscriber shape into a **blocking PR gate** using real
`tokio::sync::{mpsc, broadcast}` (not loom). Loom-shaped models remain in
[`concurrency-safety.md`](concurrency-safety.md) / `tests/loom_model.rs`.

Machine proof: `pwsh ./scripts/daemon-graph-hard-check.ps1 -SelfCheck`.

Policy manifest: [`daemon-graph-hard.json`](daemon-graph-hard.json).

Related: [`tests/daemon_graph_tokio.rs`](../../tests/daemon_graph_tokio.rs),
[`crates/sl-daemon/src/main.rs`](../../crates/sl-daemon/src/main.rs),
[`.github/workflows/daemon-graph-hard.yml`](../../.github/workflows/daemon-graph-hard.yml),
[`.github/workflows/loom-permutation.yml`](../../.github/workflows/loom-permutation.yml).

## Contract

| Stage           | Tokio primitive                              | Production mirror                   |
| --------------- | -------------------------------------------- | ----------------------------------- |
| Watcher enqueue | `mpsc::channel`                              | `CHANNEL_CAPACITY` in `sl-daemon`   |
| SSE fan-out     | `broadcast::channel`                         | `BROADCAST_CAPACITY` in `sl-daemon` |
| Lag             | `RecvError::Lagged` / `TryRecvError::Lagged` | axum SSE subscribers                |
| Shutdown        | cooperative `AtomicBool` cancel              | daemon shutdown token               |

## How to run

### SelfCheck (hermetic)

```powershell
pwsh ./scripts/daemon-graph-hard-check.ps1 -SelfCheck
```

### Live tokio graph suite

```powershell
cargo test --test daemon_graph_tokio --locked -- --test-threads=1
```

Hermetic wrapper: [`tests/daemon_graph_hard.rs`](../../tests/daemon_graph_hard.rs).

## CI / scheduling

| Gate                     | Workflow                | Mode         | Evidence                               |
| ------------------------ | ----------------------- | ------------ | -------------------------------------- |
| Loom-shaped daemon graph | `loom-permutation.yml`  | **blocking** | Retained loom models                   |
| Daemon-graph SelfCheck   | `daemon-graph-hard.yml` | **blocking** | Docs + tokio test anchors              |
| Live tokio graph suite   | `daemon-graph-hard.yml` | **blocking** | `cargo test --test daemon_graph_tokio` |

### Soft vs hard gates

| Gate                                             | Status     | Evidence                                         |
| ------------------------------------------------ | ---------- | ------------------------------------------------ |
| Live tokio mpsc/broadcast/SSE daemon graph ports | **done**   | `tests/daemon_graph_tokio.rs`                    |
| Blocking daemon-graph-hard CI workflow           | **done**   | `.github/workflows/daemon-graph-hard.yml`        |
| Daemon-graph SelfCheck                           | **done**   | `scripts/daemon-graph-hard-check.ps1 -SelfCheck` |
| `tests/daemon_graph_hard.rs` cargo wrapper       | **done**   | Hermetic SelfCheck anchor smoke                  |
| Process-level HTTP SSE soak under loom           | **unpaid** | Effort M; beyond unit graph ports                |
| Shuttle crate in default Cargo graph             | **unpaid** | C00 L7 residual                                  |

## Done / unpaid

| Item                                   | Status                       |
| -------------------------------------- | ---------------------------- |
| Policy SSOT + JSON manifest            | **done**                     |
| Live tokio pipeline conservation       | **done**                     |
| Lagged SSE subscriber recovery         | **done**                     |
| Shutdown stops mpsc enqueue            | **done**                     |
| Blocking `daemon-graph-hard.yml`       | **done**                     |
| Process-level HTTP SSE soak under loom | **unpaid** — C00 L7 residual |

<!-- Blocking daemon-graph-hard CI workflow | **done** -->
<!-- Process-level HTTP SSE soak under loom | **unpaid** -->
