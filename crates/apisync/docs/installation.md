# Installation

Apisync is a Rust library published on [crates.io](https://crates.io). Add it as a dependency:

```bash
cargo add apisync
```

or add it manually to `Cargo.toml`:

```toml
[dependencies]
apisync = "0.2"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "net"] }
```

## Toolchain

The repository pins a **nightly** Rust toolchain in `rust-toolchain.toml`:

```toml
[toolchain]
channel = "nightly"
components = ["rustfmt", "clippy", "rust-docs"]
profile = "minimal"
```

`rustup` picks the pinned toolchain automatically when you run `cargo` inside the
repository. Downstream crates that only consume `apisync` as a dependency can use
any toolchain that satisfies the edition and dependency MSRVs.

## Verify the install

```bash
cargo build
cargo test
```

Both commands must finish cleanly. The test suite covers the domain layer (unit
tests in `src/`), the hyper REST adapter (integration tests in `tests/`), and
property-based invariants in `tests/property_tests.rs`.

## Optional tooling

The repository uses the following quality gates (see the `ci.yml` / `quality-gate.yml`
workflows for the exact CI wiring):

- `cargo clippy --all-targets --all-features -- -D warnings`
- `cargo fmt --check`
- `cargo deny` for dependency advisories and license compliance
- Trunk Check (`.trunk/trunk.yaml`) for linting/formatting

## Next steps

- [Quick Start](./quickstart) — run a REST server in five minutes
- [API Reference](./api) — the public types and adapters
- [Architecture](./architecture) — how the layers fit together
