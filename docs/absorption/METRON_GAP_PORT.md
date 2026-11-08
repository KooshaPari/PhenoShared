# Metron + ObservabilityKit gap port (P1)

> Boundary owner: **PhenoObservability** (Rust metrics) + **phenotype-python-sdk** (Python facade).
> See `phenotype-registry/BOUNDARY_OWNERS.md`.

## Metron → `crates/metrickit`

| Source | Target | Status |
|--------|--------|--------|
| `<REDACTED>/Metron` `src/` | `crates/metrickit/src/` | ✅ ported |
| `Metron/tests/` | `crates/metrickit/tests/` | ✅ ported |
| `Metron/Cargo.toml` | `crates/metrickit/Cargo.toml` | ✅ workspace-aligned |
| Workspace member | root `Cargo.toml` | ✅ `crates/metrickit` |

### Post-merge (separate PRs)

1. Archive standalone `Metron` repo (redirect README → PhenoObservability).
2. Remove `HexaKit/Metron/` workspace copy (keep `templates/hexagon/rust/metrickit` scaffold only).
3. Repoint any `metrickit` git deps to `PhenoObservability` path or crates.io.

## ObservabilityKit subtree removal

| Action | Rationale |
|--------|-----------|
| Delete `ObservabilityKit/` from this repo | Triple-copy with archived repo + `phenotype-python-sdk/packages/observability-kit` |
| Python consumers | `pip install` / path dep on python-sdk package |
| Rust telemetry stubs | Use `crates/phenotype-observably-*` workspace members |

### Delete gate for archived ObservabilityKit

Safe to delete `<REDACTED>/ObservabilityKit` after this PR merges and python-sdk package is listed in SDK README kit table.

## Verification

```bash
cargo check -p metrickit
cargo test -p metrickit
```
