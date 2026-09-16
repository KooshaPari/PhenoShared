# Audit justification: heliosBench → phenotype-tooling (crates/heliosbench)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-heliosBench-batch3`
**Decision**: ABSORB → phenotype-tooling `crates/heliosbench/` (history-preserving subtree merge)

## Why absorb?

1. **History-preserving merge completed**: PR `phenotype-tooling#78` (commit
   `172ab8fd`, 2026-05-30) imported the full source tree via `git-subtree-split:
   5f85de67`. The source SHA is preserved in the merge commit body.

2. **Single-language, single-binary**: Python 3.12 hatchling build, 956 KB
   source, `helios-bench` CLI entry-point with `terminal_bench/` /
   `resource_monitor/` / `leak_detect/` / `reporters/` modules. Self-contained.

3. **Long-tail task runner**: 127 stale bot-dep issues confirm this is a
   terminal-state artifact (no community). The Python source is a measurement
   runtime, not a product surface.

4. **Canonical home verified on remote**: `phenotype-tooling/crates/heliosbench/`
   exists on `main` HEAD with Cargo.toml + Python bridge + `helios_bench/`
   package directory matching the upstream layout.

## Why not merge elsewhere

We deliberately did NOT target:
- `KooshaPari/Benchora` — Benchora is the Rust suite/eval *anchor*; heliosBench
  is the Python *measurement* runtime. Different layers.
- `KooshaPari/phenotype-tooling/crates/benchora` — same as above.
- `KooshaPari/portage` — portage is the Harbor env substrate, not a benchmark.

## State captured

| Aspect | State at absorption |
| --- | --- |
| size_kb | 956 |
| open_issues | 127 (stale bot deps) |
| stars/forks | 0 / 0 |
| last_push | 2026-08-05 |
| archived_at | 2026-08-10 |

## Absorb technique

- Subtree split (PR #78) preserving source SHA `5f85de67` in merge commit
- Squashed follow-up commits for tests + Cargo wiring
- Verified on remote HEAD via `gh api repos/KooshaPari/phenotype-tooling/contents/crates/heliosbench`

## Forward-looking note

This registry row supersedes the prior `TOO_LARGE_RETIRE` classification
(frozen 2026-07-18). DELETE-SAFE as of 2026-09-01; `gh repo delete` may be
issued once user confirmation is received.

## References

- PR `phenotype-tooling#78` (commit `172ab8fd`)
- target row: `repo-heliosBench-batch3` (registry v1.6.83)
- boundary: `docs/boundary/heliosBench.md`
- companion crate: `phenotype-tooling/crates/benchora/` (different layer, do
  not conflate)
