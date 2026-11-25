# AgilePlus Test-Gap Audit

> Generated: 2026-06-14
> Scope: all `crates/*` directories in the AgilePlus workspace (24 workspace members + 7 non-member crates)
> Method: direct source scan (`#[test]`, `#[tokio::test]`, `tests/` directories, and `pub` item heuristics). No builds executed.

---

## 1. Per-crate test inventory

| Crate | `#[test]` | `#[tokio::test]` | `tests/` files | Total test attributes |
|-------|-----------|------------------|----------------|-----------------------|
| agileplus-api | 12 | 49 | 1 | 61 |
| agileplus-application | 3 | 20 | 0 | 23 |
| agileplus-artifacts | 0 | 3 | 0 | 3 |
| agileplus-benchmarks | 19 | 6 | 0 | 25 |
| agileplus-cache | 11 | 13 | 1 | 24 |
| agileplus-cli | 199 | 25 | 0 | 224 |
| agileplus-config | 12 | 0 | 0 | 12 |
| agileplus-contract-tests | 0 | 0 | 0 | 0 |
| agileplus-dashboard | 76 | 25 | 2 | 101 |
| agileplus-domain | 41 | 2 | 0 | 43 |
| agileplus-events | 26 | 9 | 0 | 35 |
| agileplus-fixtures | 12 | 0 | 0 | 12 |
| agileplus-git | 0 | 0 | 0 | 0 |
| agileplus-github | 12 | 4 | 0 | 16 |
| agileplus-governance | 10 | 6 | 1 | 16 |
| agileplus-graph | 0 | 5 | 0 | 5 |
| agileplus-grpc | 20 | 8 | 2 | 28 |
| agileplus-import | 3 | 0 | 0 | 3 |
| agileplus-integration-tests | 8 | 69 | 6 | 77 |
| agileplus-nats | 28 | 13 | 0 | 41 |
| agileplus-p2p | 28 | 18 | 0 | 46 |
| agileplus-plane | 56 | 28 | 0 | 84 |
| agileplus-proto | 0 | 0 | 0 | 0 |
| agileplus-sqlite | 14 | 114 | 0 | 128 |
| agileplus-subcmds | 92 | 3 | 0 | 95 |
| agileplus-sync | 21 | 4 | 0 | 25 |
| agileplus-telemetry | 36 | 0 | 0 | 36 |
| agileplus-trace-validator | 11 | 0 | 2 | 11 |
| agileplus-triage | 117 | 0 | 0 | 117 |
| agileplus-validate | 9 | 0 | 0 | 9 |
| pheno-ssot-template | 6 | 0 | 1 | 6 |

**Workspace totals:** 882 `#[test]` + 424 `#[tokio::test]` = **1,306** test attributes across **16** `tests/` files.

---

## 2. Crates with ZERO tests

These crates contain **no** `#[test]` or `#[tokio::test]` attributes and have **no** `tests/` files.

1. `agileplus-contract-tests` — `crates/agileplus-contract-tests/`
2. `agileplus-git` — `crates/agileplus-git/`
3. `agileplus-proto` — `crates/agileplus-proto/`

---

## 3. Five most under-tested public modules

A *public module* is a non-test `.rs` file under `src/` that contains `pub fn`, `pub struct`, `pub enum`, `pub trait`, `pub type`, `pub use`, `pub mod`, `pub const`, `pub static`, or `pub impl` declarations. These are the modules with the largest number of public declarations and **zero** test attributes.

| Rank | File | Public declarations | First `pub` line |
|------|------|---------------------|-------------------|
| 1 | `crates/agileplus-proto/src/stubs.rs` | 68 | `stubs.rs:14` |
| 2 | `crates/agileplus-dashboard/src/templates.rs` | 42 | `templates.rs:17` |
| 3 | `crates/agileplus-application/src/dto/mod.rs` | 24 | `dto/mod.rs:16` |
| 4 | `crates/agileplus-plane/src/lib.rs` | 22 | `lib.rs:9` |
| 5 | `crates/agileplus-application/src/use_cases/triage.rs` | 19 | `use_cases/triage.rs:31` |

---

## 4. Methodology

- `#[test]` and `#[tokio::test]` were counted with a direct regex scan over every `.rs` file in `crates/`.
- `tests/` files were counted as the number of `.rs` files directly inside each crate's `tests/` directory.
- Public declarations were counted with a line-start regex (`^\s*pub\s+(fn|struct|enum|trait|type|use|mod|const|static|impl)`) on non-test source files.
- No crates were excluded; all 31 directories under `crates/` were inventoried.
