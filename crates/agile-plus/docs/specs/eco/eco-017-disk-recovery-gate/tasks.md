# Tasks: Disk Recovery Gate

## WP-01 — Scaffold `disk-gate` crate

**Deliverable:** New Rust crate at `FocalPoint/tooling/disk-gate` with `Cargo.toml`, `src/main.rs` (clap CLI), `src/lib.rs` (parsing module), and a stub `check()` returning `Ok(DiskStatus::Pass)`.

**Acceptance:**
- `cargo build -p disk-gate` succeeds.
- `disk-gate --help` prints usage.
- Crate passes `cargo clippy -- -D warnings` and `cargo fmt --check`.

**Depends on:** none.

## WP-02 — Implement check, pruner hook, and worklog emitter

**Deliverable:** Working `check()` parsing `df -k` output, pruner integration on `< 10 GiB`, and worklog event emission.

**Acceptance:**
- Unit tests cover normal, zero-byte, and malformed `df` output.
- Integration test: create a fake `target-pruner` script that frees 0 bytes → gate fails with `DISK_GATE_FAIL`; replace with one that frees 15 GiB → gate re-checks and passes.
- Worklog line is valid JSON with all required fields.

**Depends on:** WP-01.

## WP-03 — Harness integration and docs

**Deliverable:** Pre-flight snippet added to the dispatch skill and a README in the crate linking to the worklog format spec.

**Acceptance:**
- Dispatch skill docs show the `disk-gate` invocation as the first step of any cargo/worktree workflow.
- README explains thresholds (20 GiB / 10 GiB), exit codes, and worklog event schema.
- Cross-link from `docs/operations/journey-traceability.md` present.

**Depends on:** WP-02.
