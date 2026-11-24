# async-trait Migration Audit

Rust support is available: the workspace declares `rust-version = "1.86"`, so
Rust 1.75 native `async fn` in traits is not blocked by MSRV.

Current usage is not ready for a broad migration. Several async traits are used
as trait objects, including:

- `phenotype-infrastructure::ConnectionFactory`: stored as
  `Box<dyn ConnectionFactory<Connection = C>>`.
- `phenotype-security-aggregator::SecuritySource`: stored in
  `Vec<Box<dyn SecuritySource>>`.
- `agileplus-nats::EventBus`: accepted and exposed as `Box<dyn EventBus>` /
  `&dyn EventBus`.
- `agileplus-nats::Handler`: stored as `Arc<dyn Handler>`.

Native `async fn` in traits is stable, but such traits are not dyn-compatible.
Replacing `async-trait` in the object-safe port/plugin traits above would break
the current architecture unless those APIs move to generics/associated future
types or add explicit boxed-future methods.

Recommendation:

1. Keep `async-trait` for dyn-dispatched extension points and adapter ports.
2. Migrate only generic-only/internal traits after confirming they are not used
   behind `dyn`.
3. Do not remove the workspace `async-trait` dependency yet; it is still
   required by current public APIs.

Validation:

- `cargo test --workspace` failed before compile because network access to
  crates.io was unavailable while resolving `pin-project`.
- `cargo test --workspace --offline` failed before compile because the
  configured rustc wrapper `../scripts/cargo-rustc-wrapper.sh` is missing.
