# Plan: Disk Recovery Gate

## Objective

Ship a single-binary `disk-gate` pre-flight check that all fleet agents must invoke before write-heavy operations, preventing silent disk-full aborts.

## Scope

**In scope:** Rust binary `disk-gate`; integration with `target-pruner`; worklog event format; agent harness wrapper.
**Out of scope:** Linux paths, per-mount thresholds, automatic cleanup beyond `target-pruner` invocation.

## Implementation Steps

1. **Scaffold** — Create `FocalPoint/tooling/disk-gate` crate (Rust, clap-based CLI) with `Cargo.toml` and minimal `lib.rs`/`main.rs` skeleton.
2. **Core check** — Implement `check(path: &str, min_gib: u64) -> Result<DiskStatus, GateError>` using `std::process::Command` to invoke `df -k` and parse Avail into GiB. Threshold and path via CLI flags with defaults (20 GiB, `/System/Volumes/Data`).
3. **Pruner hook** — On `< 10 GiB` failure, shell out to `FocalPoint/target/release/target-pruner --prune`, then re-check; surface pruner output in the abort message.
4. **Worklog emitter** — Write structured JSON line to `$WORKLOG_DIR/events.jsonl` (or stdout if unset) with fields: `ts`, `agent`, `cmd`, `avail_gib`, `threshold_gib`, `outcome` (`pass`/`fail`/`recovered`).
5. **Harness wrapper** — Add a one-line pre-flight snippet to the dispatch skill so any worker invoking cargo/worktree tools sources `disk-gate` first.
6. **Tests** — Unit tests for `df` parsing (normal, zero, negative-spare quirks); integration test that prunes a synthetic target and confirms gate flips to `pass`.
7. **Docs** — Short README in the crate; cross-link from `docs/operations/journey-traceability.md` and the dispatch skill.

## Risks

- Disk remains full, blocking all build/test of the gate itself. Mitigation: develop on a tmpfs/staging mount when possible, defer full E2E until ≥ 20 GiB free.
