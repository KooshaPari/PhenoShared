# Logify

> Zero-cost structured logging framework for Rust.

Logify is the repository and the home of the **`logkit`** crate — a
zero-cost, structured-logging framework written in Rust, organised around
hexagonal architecture (ports & adapters) so every consumer picks the sink,
format, and runtime that fit their stack.

- **Repository:** [KooshaPari/Logify](https://github.com/KooshaPari/Logify)
- **Crate name:** `logkit`
- **Edition:** Rust 2021
- **License:** MIT OR Apache-2.0

## Why Logify / logkit?

| Feature           | Description                                                 |
| ----------------- | ----------------------------------------------------------- |
| Zero-cost         | Trait-based abstractions that the compiler erases away.     |
| Multiple sinks    | Pluggable adapters — stdout, file, network, custom.         |
| Structured logs   | First-class key/value records via `serde`.                  |
| Async support     | Built on `async-trait` for non-blocking log paths.          |
| Hexagonal design  | `domain`, `application`, `adapters`, `infrastructure`.      |

## Crate metadata

Pulled directly from `Cargo.toml`:

- **name:** `logkit`
- **version:** `0.1.0`
- **edition:** `2021`
- **description:** Zero-cost structured logging framework
- **license:** `MIT OR Apache-2.0`

## Direct dependencies

| Crate          | Version | Feature flags              |
| -------------- | ------- | -------------------------- |
| `serde`        | `1.0`   | `derive`                   |
| `serde_json`   | `1.0`   | —                          |
| `thiserror`    | `1.0`   | —                          |
| `anyhow`       | `1.0`   | —                          |
| `async-trait`  | `0.1`   | —                          |
| `parking_lot`  | `0.12`  | —                          |
| `chrono`       | `0.4`   | `serde`                    |
| `uuid`         | `1.0`   | `v4`, `serde`              |

**Dev dependencies:** `tokio` `1.0` (feature `full`).

## Architecture at a glance

```
src/
├── domain/           # Core traits & types (Logger, Level, LogEntry)
├── application/      # Use cases & orchestration (LoggerBuilder)
├── adapters/         # Pluggable sinks (stdout, file, ...)
└── infrastructure/   # Cross-cutting helpers (time, ids)
```

## Next steps

- Read [Getting Started](./getting-started.md) to build your first logger.
- Explore the source under `src/` — start with `src/domain/logger.rs` and
  `src/application/logger_builder.rs`.
- Open an issue or PR on GitHub if you find a rough edge — the project is
  intentionally a learning-focused AI-DD sandbox, so feedback is welcome.
