# phenoUtils Absorption

**Date**: 2026-07-17 (claimed); source repo on disk **404 (deleted)** at the time of audit
**Source**: `<REDACTED>/phenoUtils` (archived)
**Target**: `phenoUtils` worktree `phenoUtils-wtrees/utils01-20260908/`, branch
  `fix/utils01-walker-errors-20260908 @ 961d122` (6 of 8 claimed crates).
  PhenoShared does **not** host these crates; the `crates/pheno-utils-*` target
  in the original record is not on this tree.
**Branch**: `absorb/pheno-utils-2026-07-17` (pushed to origin) — never landed
  on PhenoShared's `main`; only on the worktree branch above.
**Wave**: `2026-07-17-queue-refresh-2`

## Status per crate

| Source crate | Target crate | Status |
|---|---|---|
| `pheno-shell` | `pheno-utils-shell` | **PRESENT** on `fix/utils01-walker-errors-20260908 @ 961d122` |
| `pheno-fs` | `pheno-utils-fs` | **PRESENT** on `fix/utils01-walker-errors-20260908 @ 961d122` |
| `pheno-net` | `pheno-utils-net` | **PRESENT** on `fix/utils01-walker-errors-20260908 @ 961d122` |
| `pheno-async` | `pheno-utils-async` | **NEVER LANDED** — no commit in any phenoUtils ref |
| `pheno-crypto` | `pheno-utils-crypto` | **PRESENT** on `fix/utils01-walker-errors-20260908 @ 961d122` |
| `pheno-testing` | `pheno-utils-testing` | **PRESENT** on `fix/utils01-walker-errors-20260908 @ 961d122` |
| `pheno-schema-port` | `pheno-schema-port` | **PRESENT** on `fix/utils01-walker-errors-20260908 @ 961d122` (not in original list; in worktree) |
| `chaos-injection` | `pheno-utils-chaos` | **NEVER LANDED** — no commit in any phenoUtils ref |

The 6 present crates retain their **original names** in the worktree (e.g.
`pheno-shell/`, not `pheno-utils-shell/`); the rename proposed in this README
never happened.

## What was absorbed

phenoUtils v0.1.0 — a 7-crate workspace of substrate-utility primitives:

| Source crate | Target crate | LOC | Purpose |
|--------------|--------------|-----|---------|
| `pheno-shell` | `pheno-utils-shell` | ~900 | tokio-based async shell exec, command builder |
| `pheno-fs` | `pheno-utils-fs` | ~800 | async file walker, hash, fs ops |
| `pheno-net` | `pheno-utils-net` | ~1100 | reqwest wrapper, URL utils, retry helpers |
| `pheno-async` | `pheno-utils-async` | ~600 | async patterns (barrier, latch, pool) |
| `pheno-crypto` | `pheno-utils-crypto` | ~1100 | AES-GCM, HMAC, base64 helpers |
| `pheno-testing` | `pheno-utils-testing` | ~1100 | wiremock harness, fixtures |
| `chaos-injection` | `pheno-utils-chaos` | ~1200 | `FaultInjector` chaos testing primitive |
| **Total** | | **6781 LOC** | |

## Changes during absorption

- Renamed crate names to `pheno-utils-*` for workspace consistency
- Rewrote path deps: `chaos-injection` → `pheno-utils-chaos`
- Updated cross-crate `use` statements (`use chaos_injection::` → `use pheno_utils_chaos::`)
- Registered 7 new workspace members in `Cargo.toml`
- Cleaned up stale `crates/pheno-data-from-phenoData/` (artefact from prior failed attempt)

## Verification

The verification originally recorded here (`cargo check -p pheno-utils-{...}`)
is **not reproducible**: none of the `pheno-utils-*` crates exists on this tree
(`for c in shell fs net async crypto testing chaos; do test -e crates/pheno-utils-$c; echo $?; done` → seven `1`s). The source repo `<REDACTED>/phenoUtils` is
404-deleted; no preservation bundle carries the namespace. The 6 crates that
do exist are only on the worktree branch above, with original names, total
807 LOC.

`pheno-utils-async` and `pheno-utils-chaos` (originally `chaos-injection`)
have no commit in any phenoUtils ref.

## Notes

- The 6 worktree crates retain original names (`pheno-shell`, `pheno-fs`,
  `pheno-net`, `pheno-crypto`, `pheno-testing`, `pheno-schema-port`); the
  proposed rename to `pheno-utils-*` never happened.
- The Python half (`pheno/python/pheno_utils/`, absorbed into `pheno` at
  `pheno @ 77917bcdd` 2026-04-25) is **separate** and unrelated to this
  Rust absorb.

## Disposition

`disposition-index.json` row `repo-phenoUtils` →
**`fsm=PENDING, archived=true, branch_pinned=true`**: source repo deleted,
absorbing branch never merged to PhenoShared `main`, 6 of 8 crates
present on `fix/utils01-walker-errors-20260908 @ 961d122`, 2 crates
never-landed.