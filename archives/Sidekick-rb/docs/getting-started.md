# Getting Started

This guide summarizes how to build, test, and lint the **Sidekick** workspace
from its [`Cargo.toml`](https://github.com/KooshaPari/Sidekick/blob/main/Cargo.toml).

## Prerequisites

- **Rust** (stable) — see `rust-toolchain.toml`
- **Cargo** — bundled with Rust
- A C toolchain (for any native build dependencies of vendored crates)

## Clone

```bash
git clone https://github.com/KooshaPari/Sidekick.git
cd Sidekick
```

## Build

Build the entire workspace in release mode:

```bash
cargo build --release --workspace
```

For a faster iteration loop:

```bash
cargo build --workspace
```

## Test

Run the full test suite:

```bash
cargo test --workspace
```

To run a single crate's tests:

```bash
cargo test -p sidekick-messaging
```

## Lint & format

Format-check (CI uses `cargo fmt --check`, you can apply changes locally with `cargo fmt`):

```bash
cargo fmt --all -- --check
```

Lint with Clippy (warnings denied):

```bash
cargo clippy --workspace --all-targets --all-features -- -D warnings
```

## Workspace layout

```
Sidekick/
├── Cargo.toml              # Workspace manifest
├── crates/
│   ├── sidekick-messaging/ # Rust crate (stub)
│   └── cheap-llm-mcp/      # Vendored Python FastMCP server
└── docs/                   # This documentation site
```

## Crates

| Crate | Type | Purpose |
|-------|------|---------|
| `sidekick-messaging` | Rust | Multi-provider messaging adapter (stub) |
| `cheap-llm-mcp` | Python (FastMCP) | Budget LLM routing |

Additional crates referenced from sibling Phenotype repos
(`sidekick-presence`, `sidekick-dispatch`) live in their respective
peer repositories.

## Publishing

Crates are published to crates.io under the `sidekick-*` prefix. Each
sub-crate is independently versioned and consumable. Version metadata is
declared in the root `Cargo.toml` under `[workspace.package]`.

## Next steps

- Browse the source on
  [GitHub](https://github.com/KooshaPari/Sidekick).
- Read [`README.md`](https://github.com/KooshaPari/Sidekick/blob/main/README.md)
  for the full architectural overview.
- Review `docs/FUNCTIONAL_REQUIREMENTS.md` in the repository for the
  requirement traceability matrix.
