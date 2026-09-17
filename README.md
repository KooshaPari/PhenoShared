> [!WARNING]
> **DEPRECATED, ARCHIVE RECOMMENDED**
> This repository has been superseded by
> [`phenotype-python-sdk/packages/data-kit`](https://github.com/KooshaPari/phenotype-python-sdk).
> This crate is a pre-alpha planning placeholder whose implemented surface is a
> single two-type sketch (not a framework). See [TOMBSTONE.md](./TOMBSTONE.md)
> for the full deprecation record.

> **Work-state:** planning | `[#---------]` | 10%
>
> Data transformation and ETL toolkit for Phenotype.
> Repository placeholder for the framework's architecture and design phase.

# DataKit

**Data transformation and ETL framework** for the Phenotype ecosystem.

A minimal Rust crate (`datakit` v0.1.0, no runtime dependencies) that sketches
the two core abstractions of the planned framework: a typed record wrapper and a
batch transformation pipeline. Everything else described in the original roadmap
(streaming, connectors, plugins, multi-backend I/O) is **planned, not
implemented**.

## Status

| Field | Value |
|-------|-------|
| Lifecycle | **DEPRECATED** (superseded by `phenotype-python-sdk/packages/data-kit`) |
| Implementation | ~10%: two public types, no I/O, no streaming, no plugins |
| Crate version | `0.1.0` (`Cargo.toml`) |
| Edition | 2021 |
| Dependencies | none (runtime); `criterion`, `rand` (dev only) |
| License | MIT (`LICENSE`) |
| Tests | 4 unit + 5 integration + 1 doc test, all passing (`cargo test --all`) |

The crate **does build, test, and lint today**. It is not a "documentation-only
placeholder". It is a working skeleton whose API is deliberately tiny.

## What actually exists

| Capability | State | Where |
|---|---|---|
| `DataStream<T>` typed record wrapper | Implemented | `src/lib.rs` |
| `Pipeline<T, U>` batch transform | Implemented | `src/lib.rs` |
| Unit tests | Implemented (4) | `src/lib.rs` (`#[cfg(test)]`) |
| Integration tests | Implemented (5) | `tests/pipeline_test.rs` |
| Doc test | Implemented (1) | `src/lib.rs` doc comment |
| Criterion benchmarks | Scaffolded | `benches/criterion_bench.rs` |
| `cargo-fuzz` target | Scaffolded | `fuzz/fuzz_target.rs` |
| Streaming engine | Not implemented | (none) |
| Connectors (files/DB/API/MQ) | Not implemented | (none) |
| Plugin architecture | Not implemented | (none) |
| Error handling / `Result` API | Not implemented (transform is infallible) | (none) |

## Quickstart

There is no CLI, no binary, and no published crate. The crate is consumed as a
library. From this repository:

```bash
cargo build          # debug build
cargo test --all     # unit + integration + doc tests
```

Using it as a path dependency:

```toml
[dependencies]
datakit = { path = "../DataKit" }
```

```rust
use datakit::{DataStream, Pipeline};

// A pipeline is a boxed, infallible, total transform.
let double  = Pipeline::new(Box::new(|x: i32| x * 2));
let add_one = Pipeline::new(Box::new(|x: i32| x + 1));

let input  = vec![DataStream::new(1), DataStream::new(2), DataStream::new(3)];
let output = add_one.run(double.run(input));

assert_eq!(
    output,
    vec![DataStream::new(3), DataStream::new(5), DataStream::new(7)]
);
```

Full type and method signatures live in
[docs/API_REFERENCE.md](docs/API_REFERENCE.md).

## Architecture

The crate is one module (`src/lib.rs`, ~94 lines) exporting two types. The
design intent and the gap analysis against the original roadmap are in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
DataStream<T> --( Vec )--> Pipeline<T, U>::run --> Vec<DataStream<U>>
                              |
                              +-- transform: Box<dyn Fn(T) -> U>
```

There is no source/sink/connector layer, no streaming layer, and no plugin
registry. `Pipeline::run` is a synchronous, in-memory `Vec` map.

## Repository layout

```
src/lib.rs                  # DataStream<T>, Pipeline<T, U> (+ 4 unit tests)
tests/pipeline_test.rs      # 5 integration tests
tests/integration/README.md # placeholder (empty suite)
tests/e2e/README.md         # placeholder (empty suite)
benches/criterion_bench.rs  # criterion benchmarks (pipeline_run, datastream_new)
fuzz/fuzz_target.rs         # cargo-fuzz target, invariants only
scripts/scorecard_ci.py     # 88-pillar repo scorecard script
docs/                       # ARCHITECTURE.md, API_REFERENCE.md
Makefile                    # build / test / lint / clean
Dockerfile, docker-compose.yml
.trunk.yaml, deny.toml, mutants.toml, codecov.yml, gitleaks.toml, renovate.json
```

## Development

All commands below were verified in this repository on 2026-09-17.

| Task | Command |
|---|---|
| Build (debug) | `cargo build` |
| Build (release) | `cargo build --release` |
| Test (all) | `cargo test --all` |
| Test (nextest, if installed) | `cargo nextest run` |
| Lint | `cargo clippy --all-targets --all-features -- -D warnings` |
| Format check | `cargo fmt --all -- --check` |
| Format apply | `cargo fmt` |
| Dependency audit | `cargo deny check` |
| Mutation testing | `cargo mutants --no-shuffle -j 2 --timeout 120` |
| Benchmarks | `cargo bench` |
| Fuzz | `cargo +nightly fuzz run fuzz_target_1` (in `fuzz/`) |
| Makefile shortcuts | `make build` / `make test` / `make lint` / `make clean` |

Full local gate:

```bash
cargo fmt --all -- --check \
  && cargo clippy --all-targets --all-features -- -D warnings \
  && cargo test --all
```

### CI

GitHub Actions workflows under `.github/workflows/`: `ci.yml` (fmt, clippy,
test, build, security), `release.yml`, `scorecard.yml`, `scorecard-ci.yml`,
`trunk-check.yml`, `mutation.yml`, `infisical.yml`,
`agileplus-pillar-scorecard.yml`.

## Known documentation inconsistencies (tracked)

These are pre-existing and not yet reconciled:

- `CLAUDE.md` states edition `2024` and license `MIT`; `Cargo.toml` declares
  edition `2021` and no `license` field (the `LICENSE` file is MIT).
- `CONTRIBUTING.md` references `anyhow`/`thiserror`/`pretty_assertions`, none of
  which are dependencies of this crate.
- `tests/integration/` and `tests/e2e/` contain only one-line README
  placeholders.
- `audit_scorecard.json` is unpopulated (`overall_score: 0`, empty pillars).
- MSRV is not pinned (`rust-version` absent from `Cargo.toml`).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md). Because this
repository is deprecated, prefer contributing to
[`phenotype-python-sdk`](https://github.com/KooshaPari/phenotype-python-sdk).

## Security

See [SECURITY.md](SECURITY.md).

## Code of Conduct

This project follows the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md).

## License

MIT. See [LICENSE](LICENSE).
