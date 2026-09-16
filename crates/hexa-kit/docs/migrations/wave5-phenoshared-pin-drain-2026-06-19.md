# Wave 5 — phenoShared git pin drain (HexaKit)

**Date:** 2026-06-19  
**Branch:** `feat/wave5-phenoshared-pin-drain`  
**ADR:** ADR-ECO-014-phenoshared-decompose  
**Gate:** `gate-phenoshared` DELETE hold until interim pins drained

## Drained to terminal DOMAIN_ROLES owners (verified on owner `main` via `gh`)

| Workspace pin | Terminal owner | Repo path |
|---------------|----------------|-----------|
| `phenotype-http-client-core` | ResilienceKit (phenotype-resilience) | `crates/phenotype-http-client-core` |
| `phenotype-state-machine` | ResilienceKit | `crates/phenotype-state-machine` |
| `phenotype-policy-engine` | ResilienceKit | `crates/phenotype-policy-engine` |
| `phenotype-auth-contracts` | Authvault | `rust/phenotype-auth-contracts` |
| `phenotype-event-contracts` | Eventra | `rust/phenotype-event-contracts` |
| `phenotype-agent-contracts` | Agentora | `rust/phenotype-agent-contracts` |
| `phenotype-security-aggregator` | Authvault | `authkit/rust/phenotype-security-aggregator` |

## Remaining phenoShared interim pins (blocked)

| Pin | Blocker |
|-----|---------|
| `phenotype-event-bus`, `phenotype-event-sourcing` | Not on Eventra `main` (only `phenotype-event-contracts` landed) |
| `phenotype-time` | Not on `phenotype-types` or `phenotype-config` `main` |
| `phenotype-async-traits`, `phenotype-macros` | `phenotype-rust-sdk` repo does not exist |
| `phenotype-health` | PO `rust/phenotype-health` API diverges (`HealthCheck` vs `HealthChecker`) |
| `phenotype-cache-adapter` | **Drained** — inline HexaKit stub `crates/phenotype-cache-adapter-stub` (2026-06-19) |
| `phenotype-contracts` | Generic `Contract` trait — interim until rust-sdk facade |
| `phenotype-iter`, `phenotype-string`, `phenotype-validation` | Still only on phenoShared `main` |

## Drained (2026-06-19)

| Pin | Replacement |
|-----|-------------|
| `phenotype-cache-adapter` | HexaKit path stub `crates/phenotype-cache-adapter-stub` — **zero phenoShared git deps in HexaKit** |

## Verification

```bash
cargo check -p phenotype-core
rg '<REDACTED>/phenoShared' Cargo.toml
```
