# Absorption Record — Benchora

## Transfer Record

| Field | Value |
|-------|-------|
| Source repo | `<REDACTED>/Benchora` |
| Target repo | `<REDACTED>/phenotype-tooling` |
| Target path (in target repo) | `Benchora/` (tooling root) |
| Absorb commit | `f1f9a025` (PR #322, 2026-09-13) |
| Absorbed date | 2026-07-17 (original); 2026-09-13 (re-absorbed into current path) |
| Absorbed by | forge agent (batch absorption) |
| Verification | `git ls-tree -r main | grep -c '^.*\tBenchora/'` → 138 files at tooling root on `main` |

## What was absorbed

Single Rust crate: 138 files at tooling root (re-absorbed 2026-09-13 via PR #322,
commit `f1f9a025`). The earlier `benchora` stub (v0.1.0, 19-line `lib.rs`)
was removed in commit `d7480faa` (2026-09-11) as part of PR #313. The "v0.2.0,
78 files" wording here predates the re-absorption and no longer matches either
tree; superseded by the count above.
