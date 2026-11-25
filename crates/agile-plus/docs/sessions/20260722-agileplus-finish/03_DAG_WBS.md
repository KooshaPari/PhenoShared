# Delivery DAG and Work Breakdown

## Dependency graph

`T1 generated build + resolved runtime` -> `T3 durable events` -> `T4 artifacts + API/gRPC/MCP cursor stream` -> `T5 AgilePlus evidence` -> `T6 Tracera` -> `T7 Grapheon` -> portfolio.

`T1` -> `T2 encrypted credentials/API keys` -> `T3`; `T1` -> `T4`. T2 can run in parallel with the runtime part of T1, but its reference-only data contract must land before T3 and T5.

## Work packages and gates

| ID | Owner lane | Depends on | Definition of done | Required proof |
|---|---|---|---|---|
| T1 | runtime | none | generated proto only; one port resolver; real API/gRPC lifecycle | locked package tests, live health/gRPC/shutdown transcript |
| T2 | security | build baseline | keychain-first encrypted fallback and API-key redaction | crypto/tamper/rotation tests plus secret scan |
| T3 | events | T1,T2 | SQLite query + stable cursor + audit chain | restart/filter/cursor/chain contract tests |
| T4 | evidence transport | T1,T3 | MinIO digest store and single resumable authenticated stream source | MinIO authorization/digest tests and live SSE/gRPC/MCP transcript |
| T5 | AgilePlus dogfood | T2-T4 | verifier accepts only complete self-dogfood manifest | real commands, trace, usage, artifact, audit, manifest verification |
| T6 | Tracera dogfood | T5 | full consuming-project evidence pack | project-scoped integration test and verifier pass |
| T7 | Grapheon recovery/dogfood | T6 | no conflict markers, clean build, consuming-project evidence pack | conflict scan, build/test, verifier pass |
| T8 | portfolio | T7 | one independently verifiable go/no-go record per project | per-project manifest and command transcript |

## Parallelization and checkpoints

- Begin T1 and T2 on separate branches. Do not merge T3 until both contracts are reviewed.
- Begin T4 only after T3 exposes a tested cursor. T5 begins only with T2-T4 green.
- Each task owns its new tests and commits a focused slice. The integrator runs `cargo test --workspace --locked` after T5, T6, and T7.
- Before each external consumer runtime test: inspect port ownership; use isolated compose resources and development-only credentials. Before every completion claim: run the evidence verifier.
