# P4 contracts slice 2 — auth/policy traits (Authvault)

**Date:** 2026-06-18  
**Disposition:** D-01 slice 2  
**Source interim:** phenoShared `crates/phenotype-contracts` (generic traits only — slice 1)  
**Terminal owner:** Authvault  
**Plan:** [phenotype-registry contracts-decompose-plan](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/disposition/contracts-decompose-plan.md)

## Target layout

| Surface | Canonical path |
|---------|----------------|
| Auth port traits (`AuditSink`, `RevocationStore`, `RefreshTokenStore`, `PasswordHasher`, `KeyManagementService`) | `rust/phenotype-auth-contracts/src/auth.rs` |
| Policy contract traits (`PolicyEvaluator`, `AuthorizationContext`, `PolicyEffect`) | `rust/phenotype-auth-contracts/src/policy.rs` |

## Scope

- **In:** trait-only auth/policy contracts extracted from Authvault domain ports.
- **Out:** generic `Contract` / `Event` / `MetricsHook` (remain phenoShared interim per slice 1).
- **Out:** AuthKit vendored generic `phenotype-contracts` (not auth-related per Block-C audit).

## Consumer repoint

| Consumer | Action |
|----------|--------|
| `phenotype-python-sdk` `packages/auth-kit/rust` | Git-pin `phenotype-auth-contracts` from Authvault; drop vendored generic copy |
| Authvault `src/domain/ports.rs` | Future slice: depend on / re-export contracts crate (not required for slice 2 landing) |

## Verification

```bash
cargo check -p phenotype-auth-contracts
```

## Registry

Row **#11** (`phenotype-contracts`) stays `fsm: relocating` — slice 2 partial; slices 3–4 pending.
