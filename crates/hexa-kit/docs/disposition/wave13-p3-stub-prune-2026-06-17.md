# Wave 13 — P3 git-pinned crate stub prune (2026-06-17)

**Builds on:** P3 waves 2–4 (#256, #258, #260), wave 12 (#261), eco-consolidate (#255)

## Action

Remove local `Cargo.toml` + `src/` from workspace-**excluded** crates already git-pinned to phenoShared. Retain `MIGRATED.md` redirect stubs only.

| Crate | phenoShared git pin since |
|-------|---------------------------|
| `phenotype-error-core` | #252 |
| `phenotype-errors` | #252 |
| `phenotype-event-sourcing` | #256 |
| `phenotype-logging` | #258 |
| `phenotype-time` | #258 |
| `phenotype-state-machine` | #258 |
| `phenotype-policy-engine` | #258 |
| `phenotype-security-aggregator` | #260 |
| `phenotype-async-traits` | #260 |
| `phenotype-macros` | #260 |
| `phenotype-health` | #261 |
| `phenotype-cache-adapter` | #261 |

## Verification

```bash
cargo check -p phenotype-core -p hexakit-cli
```
