# G2 chokepoint repoint — PhenoObservability (2026-06-17)

**Wave:** G2  
**Chokepoint ID:** `PhenoObservability`  
**Registry:** [chokepoints.json](https://github.com/KooshaPari/phenotype-registry/blob/main/registry/chokepoints.json)

## Objective

Remove git dependencies on `<REDACTED>/HexaKit` for cross-cutting infra crates so
Traceon / ObservabilityKit archive is not blocked by HexaKit monorepo paths (v2
charter repoint, not monorepo absorb).

## Changes

| Manifest | Before | After |
| --- | --- | --- |
| Root `Cargo.toml` | `phenotype-errors`, `phenotype-event-bus` → HexaKit git | Path deps under `vendor/` |
| Root `Cargo.toml` | — | `phenotype-error-core` → `<REDACTED>/phenoShared` git |
| `rust/Cargo.toml` | `phenotype-error-core` → HexaKit git | `<REDACTED>/phenoShared` git |
| `crates/phenotype-mcp-server/Cargo.toml` | `phenotype-errors` → HexaKit git | Path to `vendor/phenotype-errors` |

## Vendored crates

Copied from HexaKit @ main (2026-06-17):

- `vendor/phenotype-errors` — facade over `phenotype-error-core`
- `vendor/phenotype-event-bus` — in-memory bus + trait surface

Both vendor manifests depend on `phenotype-error-core` from **phenoShared**, which
is already the canonical home per [DOMAIN_ROLES](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/DOMAIN_ROLES.md).

## Follow-up

1. **phenoShared Wave E** — publish `phenotype-errors` and `phenotype-event-bus`
   on `main`, then replace `vendor/` path deps with phenoShared git + `package`.
2. **Delete `vendor/`** once git deps resolve cleanly.
3. **CI secrets** — `.github/workflows/test.yml` still fetches private
   `phenotype-event-bus` tarballs; unrelated to this repoint but blocks full CI green.

## Verification

```powershell
cd PhenoObservability
rg '<REDACTED>/HexaKit' Cargo.toml rust/Cargo.toml crates/**/Cargo.toml vendor/**
# expect: no matches on repointed deps
cargo check --workspace
```

## Status

**Repointed** — no remaining HexaKit git deps for `phenotype-errors` /
`phenotype-event-bus` / `phenotype-error-core` in active workspace manifests.

