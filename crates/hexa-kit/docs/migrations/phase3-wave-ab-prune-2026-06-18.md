# Phase 3 Wave A/B — HexaKit stub prune (2026-06-18)

**Prereq:** phenoShared #190 on `main` (`95d74795`); PhenoObservability `phenotype-sentry-config` on main (#168); TestingKit `phenotype-contract` (#9).

## Workspace exclude + git pin

| Crate | Target | Registry id |
|-------|--------|-------------|
| `phenotype-sentry-config` | PhenoObservability | 35 |
| `phenotype-telemetry` | PhenoObservability | 39 |
| `phenotype-logging` | PhenoObservability | 26 |
| `phenotype-contract` | TestingKit | 10 |
| `phenotype-test-fixtures` | TestingKit | 41 |

## phenoShared pin refresh (E2a utils → main)

| Crate | Branch |
|-------|--------|
| `phenotype-iter` | `main` |
| `phenotype-string` | `main` |
| `phenotype-validation` | `main` |

## Stub prune

Removed local `Cargo.toml` + `src/` from excluded crates; retained `MIGRATED.md` only.

## Verification

```bash
cargo check -p phenotype-core
```
