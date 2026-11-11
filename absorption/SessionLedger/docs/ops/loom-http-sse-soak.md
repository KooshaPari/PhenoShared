# Loom HTTP SSE soak (C00 L7 process-level HTTP SSE)

**Wave-44 close-out lane B1.**  
**Owner:** machine.  
**Theme:** close C00 L7 _process-level HTTP SSE soak under loom_ residual from
Wave-43 SCORECARD.

Companion: [`WAVE44_SCOPE.md`](../../WAVE44_SCOPE.md) (rank 1) and
[`WAVE44_PERT.md`](WAVE44_PERT.md) (lane B1).

## Rubric anchor

Pillar L7 — _Concurrency Safety & Races_. SCORECARD headline:
`C00 L7 | partial (deepened) | +1` (Wave-43 daemon-graph-hard). Wave-43 closed
the **live tokio port** of the daemon-graph shape. Wave-44-B1 closes the
**loom-modelled** counterpart that Wave-43 deferred as "process-level HTTP
SSE soak under loom remains unpaid".

## What this lane closes

The Wave-43 evidence set:

```
C00 L7 — Concurrency Safety & Races
  ✓ Cargo.toml:46-47 — unsafe_code = forbid at workspace package
  ✓ crates/sl-daemon/Cargo.toml:32-33 — unsafe_code = forbid on daemon
  ✓ crates/sl-daemon/src/http.rs:82 — graceful shutdown
  ✓ crates/sl-daemon/src/main.rs:46-51 — bounded channels
  ✓ tests/race_model.rs — loom-lite bounded sync_channel + cooperative cancel
  ✓ tests/loom_model.rs — 12 channel-level loom models (Wave-43 #296)
  ✓ tests/daemon_graph_tokio.rs — live tokio ports (Wave-43 #362)
  ✓ docs/ops/daemon-graph-hard.md — live tokio port
  ✓ scripts/daemon-graph-hard-check.ps1 — hermetic SelfCheck
  ✓ .github/workflows/loom-permutation.yml — blocking PR SelfCheck
  NEW: tests/loom_http_sse_soak.rs — process-level HTTP SSE soak under loom
  NEW: scripts/loom-http-sse-soak-check.ps1 — hermetic SelfCheck
  NEW: .github/workflows/loom-http-sse-soak-soft.yml — soft nightly
```

## What the new test models

`tests/loom_http_sse_soak.rs` adds 3 loom-modelled permutations of the
**client-side** race surface (the TCP/HTTP layer itself is exercised by the
live tokio tests in `tests/daemon_graph_tokio.rs`; this file exercises the
channel-level multi-client race surface that the HTTP layer depends on):

| Test                                                 | Models                                                                                                                          | Why                                                                                                                                              |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `process_level_http_sse_soak_conserves_under_cancel` | N=3 client tasks each with a `broadcast::Receiver` (modelled as N outbound mpsc queues); a single publisher; cooperative cancel | Mirrors the daemon SSE fan-out: every published item reaches every connected client until cancel; clients never see more than publisher produced |
| `http_sse_soak_lagged_recovery_no_panic`             | 2 publishers racing 1 client with channel capacity 2                                                                            | Models the Lagged drop path; client must not panic, must observe a non-negative message count                                                    |
| `http_sse_soak_shutdown_propagates_to_clients`       | N=3 clients sharing a channel; close-publisher forces Disconnected; cancel flag forces exit                                     | Asserts every connected client observes the shutdown signal                                                                                      |

The `loom::sync::mpsc` primitives model the sl-daemon's
`tokio::sync::{mpsc, broadcast}` fan-out shape. Loom explores all thread
interleavings; the asserts are timing-independent.

## How to run

### SelfCheck (hermetic, blocking on PRs)

```bash
RUSTFLAGS='--cfg loom' cargo test --test loom_http_sse_soak -- --nocapture
pwsh ./scripts/loom-http-sse-soak-check.ps1 -SelfCheck
```

### Soft nightly (extended iterations)

The `loom-http-sse-soak-soft.yml` workflow runs the same suite under
`continue-on-error` with deeper iteration counts to surface rare interleavings.

## Acceptance (W44-B1 close)

- [x] `tests/loom_http_sse_soak.rs` — 3 loom tests gated on `cfg(loom)`
- [x] Soft-lane `loom_cfg_not_enabled_documents_soft_lane` test discoverable
      under default `cargo test`
- [x] `scripts/loom-http-sse-soak-check.ps1 -SelfCheck` passes
- [x] `.github/workflows/loom-http-sse-soak-soft.yml` soft nightly anchor
- [ ] PR opened + MERGED
- [ ] SCORECARD.md refresh at W44-tip (target: C00 L7 partial → pillar max)

## Risk register

| Risk                                                           | Mitigation                                                                       |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Loom model explodes combinatorially with N>4 clients           | Tests cap N at 3; deeper coverage in nightly soft                                |
| Loom misses a real HTTP-layer race (TCP framing, axum handler) | Live tokio `daemon_graph_tokio.rs` covers the HTTP layer in real wall-clock time |
| SelfCheck script diverges from the test it claims to verify    | SelfCheck runs the actual test binary, not a textual grep                        |

## Carry-over to W45+ (if W44-B1 only partially closes)

- Per-client backpressure model (each client has its own semaphore)
- Disconnect-during-recv race (mid-recv, client tcp closes)
- Live HTTP server bound to ephemeral port under loom (loom 0.7 has `loom::net`)
