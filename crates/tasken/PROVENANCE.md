# Provenance: tasken crate

## Origin

This crate was absorbed from **[zz-Tasken](https://github.com/KooshaPari/zz-Tasken)**.

## Source Repository

- **Repository:** https://github.com/KooshaPari/zz-Tasken
- **Commit:** `d02adf6c2fc02dde1241251a751088351973e484`
- **Commit message:** `chore(deps): bump thiserror from 2.0.18 to 2.0.19 (#99)`
- **Date:** 2026-09-12
- **Original package name:** `taskkit`
- **Absorbed as:** `tasken` (renamed to avoid collision with any future `taskkit` crate)

## Absorption Date

2026-09-13

## What Was Absorbed

All Rust source code from zz-Tasken, including:

### Source files (`src/`)
| File | Lines |
|------|-------|
| `src/domain/recipes.rs` | 1,125 |
| `src/adapters/primary/cli.rs` | 916 |
| `src/application/services.rs` | 813 |
| `src/infrastructure/otel.rs` | 774 |
| `src/domain/recipe.rs` | 739 |
| `src/application/import.rs` | 656 |
| `src/domain/plugins.rs` | 579 |
| `src/domain/tasks.rs` | 526 |
| `src/domain/stream_runner.rs` | 454 |
| `src/domain/rate_limiter.rs` | 409 |
| `src/infrastructure/persistent_cache.rs` | 362 |
| `src/application/visualize.rs` | 331 |
| `src/application/forwarded.rs` | 330 |
| `src/domain/runners.rs` | 316 |
| `src/domain/workflows.rs` | 269 |
| `src/domain/scheduler.rs` | 254 |
| `src/adapters/secondary/file.rs` | 248 |
| `src/domain/errors.rs` | 230 |
| `src/adapters/secondary/memory.rs` | 227 |
| `src/application/watcher.rs` | 225 |
| `src/adapters/primary/color_choice.rs` | 213 |
| `src/config/mod.rs` | 203 |
| `src/cron_parser.rs` | 172 |
| `src/domain/events.rs` | 170 |
| `src/infrastructure/cache.rs` | 143 |
| `src/infrastructure/observability.rs` | 123 |
| `src/domain/groups.rs` | 121 |
| `src/application/commands.rs` | 120 |
| `src/adapters/plugins/mod.rs` | 115 |
| `src/domain/ports.rs` | 105 |
| `src/application/queries.rs` | 81 |
| `src/lib.rs` | 52 |
| `src/main.rs` | 44 |
| `src/domain/mod.rs` | 44 |
| `src/infrastructure/error.rs` | 30 |
| `src/infrastructure/mod.rs` | 18 |
| `src/application/mod.rs` | 16 |
| `src/adapters/mod.rs` | 10 |
| `src/adapters/secondary/mod.rs` | 8 |
| `src/adapters/primary/mod.rs` | 8 |
| **Total source** | **~9,340** |

### Test files (`tests/`)
| File | Lines |
|------|-------|
| `tests/integration.rs` | 686 |
| `tests/runtime.rs` | 381 |
| `tests/cli_and_entry.rs` | 345 |
| `tests/cron_parser.rs` | 223 |
| `tests/oracle_acceptance.rs` | 5 |
| **Total tests** | **~1,640** |

### Grand Total: ~13,219 lines of Rust code

## Cargo.toml Adaptations

When absorbing into the workspace, the following changes were made to `Cargo.toml`:

1. **Removed `[workspace]` section** — this crate is now a member of the phenotype-tooling workspace
2. **Renamed package** from `taskkit` to `tasken`
3. **Switched to workspace dependencies** where available:
   - `tokio`, `serde`, `serde_json`, `chrono`, `clap`, `thiserror`, `anyhow`, `uuid`, `tracing`, `tracing-subscriber`, `serde_yaml`
4. **Kept external dependencies** not in workspace:
   - `cron-parser`, `petgraph`, `async-trait`, `futures`, `dotenvy`, `libc`, `notify`, `dirs`, `envy`, `toml`, `opentelemetry`
5. **Preserved features** (`otel` optional feature)

## What Was NOT Absorbed

The following non-Rust files from zz-Tasken were intentionally not copied:
- Python scripts (`python/` directory) — not part of the Rust crate
- CI/CD configs (`.circleci/`, `.github/`)
- Documentation files (docs, README, CHANGELOG, etc.)
- Configuration files (`.editorconfig`, `.pre-commit-config.yaml`, etc.)
- `Taskfile.yml`, `Dockerfile`, `package.json`
- Build artifacts and lock files (`Cargo.lock`, `package-lock.json`)

These may be absorbed separately if needed.

## License

The absorbed code retains its original dual MIT/Apache-2.0 license from zz-Tasken.
