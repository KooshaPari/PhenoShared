# Boundary — phenotype-config

> Federated `phenotype-config` config crate. Boundary file created
> 2026-07-17 during registry batch4 refresh. Distinct from `phenoConfig`
> (separate repo, different scope) and from `pheno-runtime-config`
> (absorbed 2026-07-17 into `pheno` monorepo).

## In Scope

- **Federated config schema** — Pydantic (Python) + Zod (TypeScript) +
  Rust schema for the `phenotype-config` types (config loader,
  env-var binding, file-source, vault-source).
- **Validators** — runtime invariant checks, secret redaction,
  pattern-enforcement.
- **Multi-language bindings** — same schema published as Rust crate,
  Python package, TypeScript types via `pyo3`/`napi-rs` machinery.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| Config loading mechanism | `pheno` monorepo `crates/phenotype-config/` | The federated crate only defines schema |
| Runtime reload | `pheno-runtime-config` (in `pheno`) | ADR-095 Reloadable<T> pattern |
| Vault storage | `Authvault` (AuthKit absorbed) | Secret material lives in vault |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| Apps → phenotype-config | consumer | schema import | green |
| phenotype-config → `Configra` | peer | legacy config loader | amber (migration in progress) |

## Last Boundary Review

**Date:** 2026-07-17
**Reviewer:** registry batch4 audit (queue-refresh-batch4)
**Disposition-index row:** DSPI-NEW (`repo-phenotype-config`, fsm=queued)
**Decisions:**
- ABSORB target: `pheno` monorepo `crates/phenotype-config/`.
- Federated — Python and TS bindings live in their respective
  monorepos (phenotype-python-sdk, phenodocs).

**Next review:** on absorption completion
