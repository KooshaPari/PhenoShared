# Getting Started

This guide walks you through building your first `logkit` logger, mirroring
the usage snippet from the project README.

## Prerequisites

- **Rust** stable (edition 2021)
- **Cargo** (bundled with Rust)

Verify your toolchain:

```bash
rustc --version
cargo --version
```

## Add `logkit` as a dependency

In your `Cargo.toml`:

```toml
[dependencies]
logkit = "0.1"
```

## Build your first logger

The builder pattern exposed by `logkit::LoggerBuilder` lets you pick a name
and a minimum level before constructing the logger:

```rust
use logkit::{LoggerBuilder, Level};

let logger = LoggerBuilder::new("app")
    .level(Level::Info)
    .build();

logger.info("service started");
```

::: tip Placeholder credentials
If you ever wire `logkit` into a remote sink that requires a token, supply
it via an environment variable — never hard-code secrets. Example using
the `env!` macro at build time:

```rust
let token = env!("LOGKIT_API_TOKEN", "Set LOGKIT_API_TOKEN to your API token");
```

The literal placeholder value here is **`YOUR_API_TOKEN`**; the real value
must come from your environment, secret manager, or CI secret store.
:::

## Run the test suite

From the repository root:

```bash
cargo test --workspace
```

This exercises the domain, application, and adapter modules end-to-end.

## Project layout

| Path                          | Role                                  |
| ----------------------------- | ------------------------------------- |
| `src/domain/`                 | Core traits: `Logger`, `Level`, etc.  |
| `src/application/`            | `LoggerBuilder` & orchestration       |
| `src/adapters/`               | Sink implementations (stdout, file…)  |
| `src/infrastructure/`         | Shared helpers (time, ids, …)         |

## What to read next

- The `Logger` trait in `src/domain/logger.rs` — every sink implements it.
- `Level` in `src/domain/log_level.rs` — how severity is filtered.
- `LoggerBuilder` in `src/application/logger_builder.rs` — fluent setup.

When you're ready to deploy your own sink, copy one of the adapters under
`src/adapters/sinks/` and implement the `Logger` trait.
