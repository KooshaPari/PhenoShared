# airlock-v2 (Rust port)

Conservative auto-save / push daemon for git repositories. This crate
is a Rust port of the original `airlock-v2.py` engine (vendored from
`~/.airlock/bin/`). The two daemons share state at `~/.airlock/v2/` —
schema is byte-compatible.

## Why port?

The Python engine is single-threaded and has no structured logging. The
Rust port:

- Adds explicit types for `RepoEntry`, `AutocommitRecord`,
  `CleanupRecord`, `Registry` (with serde compatibility on both shapes).
- Keeps the same CLI surface (register/unregister/list/status/snapshot/
  autocommit/cleanup) but exposes the underlying cycles as library
  functions so callers can compose them.
- Replaces `argparse --dry-run` with a single boolean flag.
- Uses `std::process::Command` exclusively for git operations (matching
  `crates/worktree-manager`).
- Never calls `git push --force` or `git push --atomic --force-with-lease`.
  FF-only; on rejection, falls back to `wip/<date>-<uuid>` snapshot.

## Build

```sh
cargo build -p airlock-v2 --release
```

## Run

```sh
# Single-shot 15-minute autocommit pass:
target/release/airlock-v2 autocommit

# Single-shot 8-hour cleanup pass:
target/release/airlock-v2 cleanup --dry-run

# Register a repo:
target/release/airlock-v2 register /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoVCS

# Audit every registered repo:
target/release/airlock-v2 audit

# Long-running scheduler (called by launchd):
cargo run --release --example daemon -- autocommit
```

## Layout

- `src/lib.rs` — `StateRoot`, intervals, error-free constructors.
- `src/registry.rs` — JSON read/write with schema compat.
- `src/git_ops.rs` — shell-out git helpers; **no `git2`**.
- `src/autocommit.rs` — 15-min cycle.
- `src/cleanup.rs` — 8-hr cycle.
- `src/cli.rs` — clap-based dispatch.
- `src/main.rs` — binary entry.
- `examples/daemon.rs` — long-running scheduler.
- `docs/ADAPTATION.md` — Python → Rust notes.

## Test

```sh
cargo test -p airlock-v2
```

Tests use `tempfile` to create ephemeral git repos; no network is
required.

## See also

- `docs/ADAPTATION.md` — full port-and-upgrade notes.
- `~/CodeProjects/Phenotype/repos/.airlock/bin/airlock-v2.py` — original
  Python engine.
