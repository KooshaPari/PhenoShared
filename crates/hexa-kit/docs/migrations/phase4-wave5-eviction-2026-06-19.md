# Phase 4 wave 5 — HexaKit eviction (tasks 56–70)

**Date:** 2026-06-19  
**Predecessor:** Phase 3 Wave A/B ([#271](https://github.com/KooshaPari/HexaKit/pull/271)), Wave H ([#269](https://github.com/KooshaPari/HexaKit/pull/269))

## Workspace exclude + git pin

| Crate | Target | Task |
|-------|--------|------|
| `phenotype-validation` | phenoShared | #57 (done #271) |
| `phenotype-string` | phenoShared | #58 (done #271) |
| `libs/phenotype-config-core` | phenoShared (H14 interim) | #59 |

## phenotype-core re-export API diverge (task #56)

Resolved by aligning re-exports to canonical git-pinned surfaces:

| Module | HexaKit legacy | Canonical (git pin) | Resolution |
|--------|----------------|---------------------|------------|
| `config` | struct `ConfigLoader` | trait `ConfigLoader` + `Priority` | Re-export trait surface from phenoShared |
| `state_machine` | local path | phenoShared `StateMachine` | Git pin wave 3 (#258) |
| `cache` | local path | phenoShared `CacheAdapter` | Git pin wave 12 (#261) |
| `time` | local path | phenoShared `Timestamp` | Git pin wave 3 (#258) |

## Stub prune (#262 pattern, task #62)

| Path | Action |
|------|--------|
| `libs/phenotype-config-core` | Remove `Cargo.toml` + `src/`; `MIGRATED.md` only |
| `crates/phenotype-string` | Remove orphan `src/` (partial prune from #271) |
| `crates/phenotype-config-core` | Remove orphan duplicate `src/lib.rs` |
| `crates/phenotype-sentry-config` | **Remove tree entirely** (PO #168 absorbed; task #64) |

## Workspace member audit (task #70)

**15 workspace members** (scaffold-only target):

| Member | Role |
|--------|------|
| `hexakit-cli` | Scaffold CLI |
| `phenotype-contract-adapters` | HexaKit-local adapter scaffold |
| `phenotype-contract-tests` | Template CI harness |
| `phenotype-compliance-scanner` | Governance-only |
| `phenotype-cost-core` | Scaffold-adjacent |
| `phenotype-error-macros` | Scaffold macros |
| `phenotype-git-core` | Scaffold-adjacent |
| `phenotype-port-traits` | Port traits (bootstrap) |
| `phenotype-ports-canonical` | Port canonicalization |
| `phenotype-process` | Scaffold-adjacent |
| `phenotype-shared-config` | Scaffold-adjacent |
| `phenotype-core` | Umbrella re-exports (git-pinned deps) |
| `phenotype-infrastructure` | Resilience patterns |
| `phenotype-project-registry` | Scaffold registry |
| `phenotype-xdd-lib` | XDD harness |
| `forgecode-fork` | Forge boundary (Tasken TBD) |

**52 excluded** paths (git-pinned or archived stubs).

## Verification

```bash
cargo check --workspace
cargo check -p phenotype-core
```
