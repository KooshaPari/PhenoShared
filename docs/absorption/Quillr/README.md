# Quillr + Httpora Absorption

## Wave

`2026-07-17-queue-refresh` (continuation after first 7 of 10 from
the wave completed)

## What was absorbed

**Quillr v1.0.1** (the merged identity that subsumes Httpora)
absorbed from `<REDACTED>/Quillr` into two spine targets:

| Half | Language | Target | Where it lives | Status |
|------|----------|--------|----------------|--------|
| `crates/httpora-core` | Rust | `pheno` monorepo | `crates/httpora-core/` | ✅ absorbed (commit `absorb/httpora-core-2026-07-17`) |
| `src/` (`@<REDACTED>/quillts`) | TypeScript | — (standalone) | `repos/Quillr/src/` (not in PhenoShared tree) | ❌ **NOT absorbed into PhenoShared**. The TS half lives only in the standalone `Quillr` checkout at `repos/Quillr/src/`; the README's 2026-07-17 claim of `phenodocs/packages/quillts/` was incorrect (FORWARD-WBS §5: "quillts negative strengthened. The `phenodocs` checkout exists at `_full_pheno/phenodocs`; its `packages/` tree object holds only pheno-core/pheno-llm/pheno-resilience — **no quillts**, and no quillts commit in any phenodocs ref"). The intended phenodocs repo never merged the absorb. |

## Identity reconciliation

`Httpora` was already SUPERSEDED by `Quillr` per disposition-index
row `history` (2026-06-20). The `<REDACTED>/Httpora` repo no longer
exists — its content was merged into Quillr as `crates/httpora-core`.
The "Quillr + Httpora reconcile identity/name" decision in
`RATIONALIZATION_PLAN.md` is therefore resolved by absorbing Quillr
itself (which carries both halves).

Final naming:

- **Rust crate**: `httpora-core` (kept name; descriptive of the HTTP
  middleware responsibilities it implements)
- **TypeScript package**: `@phenotype/quillts` (renamed from
  `@<REDACTED>/quillts` for the Phenotype org; "quill" hints at the
  'trace/quill' branding)

## Content

### httpora-core (Rust)

- `src/lib.rs` — entry, re-exports
- `src/error.rs` — error types
- `src/builder.rs` — builder pattern
- `src/middleware/` — 7 modules: `cors.rs`, `otel.rs`, `retry.rs`,
  `rate_limit.rs`, `circuit_breaker.rs`, `clock.rs`, `mod.rs`
- `tests/` — 5 files: `acceptance.rs`, `circuit_breaker.rs`,
  `cors.rs`, `rate_limit.rs`, `retry.rs`
- `Cargo.toml` with feature gates (`full`, `tower`, `serde`,
  `serde_json`)

### @phenotype/quillts (TypeScript)

- `src/client.ts` — HTTP client
- `src/interceptor.ts` — request/response interceptor
- `src/mock.ts` — mock transport
- `src/retry.ts` — retry logic
- `src/types.ts` — type definitions
- `src/index.ts` — entry point
- `src/__tests__/` — 5 files: `client.test.ts`,
  `traceability.test.ts`, `mock.test.ts`, `benchmark.test.ts`,
  `acceptance.test.ts`

## Verification

| Crate / Package | Command | Result |
|-----------------|---------|--------|
| `httpora-core` | `cargo check` | Finished in 10.28s, clean |
| `httpora-core` | `cargo test` | 60 tests passing, 1 ignored |
| `quillts` | (test wiring pending — to be added once `@phenotype/quillts` is wired into phenodocs workspace deps) | n/a |

## Source repo

`<REDACTED>/Quillr` archived on GitHub 2026-07-17.

## Disposition

- `repo-Quillr` row updated in disposition-index to `fsm=absorbed`,
  `archived=true`
- Two absorption branches recorded:
  - `absorb/httpora-core-2026-07-17` (Rust half → `pheno`)
  - `absorb/quillts-2026-07-17` (TS half → `phenodocs`)
- Source repo archived; the Httpora question is permanently resolved
  since the source identity has been subsumed.