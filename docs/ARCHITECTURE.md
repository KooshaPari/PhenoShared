# DataKit Architecture

> Status: **DEPRECATED** as of 2026-09-17. Superseded by
> `phenotype-python-sdk/packages/data-kit`. This document describes the
> repository as it actually is, not as originally planned. See
> [../TOMBSTONE.md](../TOMBSTONE.md).

## 1. Scope of this document

This documents the implemented architecture of the `datakit` crate. Because the
crate is a ~94-line planning skeleton, the honest architecture is short. Section
6 records the gap between the implemented design and the original roadmap so
that the gap is not mistaken for missing documentation.

## 2. Crate identity

| Property | Value | Source |
|---|---|---|
| Crate name | `datakit` | `Cargo.toml` |
| Version | `0.1.0` | `Cargo.toml` |
| Edition | 2021 | `Cargo.toml` |
| Runtime dependencies | none | `Cargo.toml` `[dependencies]` |
| Dev dependencies | `criterion` 0.5 (html_reports), `rand` 0.8 | `Cargo.toml` |
| License | MIT | `LICENSE` (no `license` field in `Cargo.toml`) |
| Library type | `lib` (no `[[bin]]`) | `Cargo.toml` |
| Fuzz crate | `datakit-fuzz` (publish = false) | `fuzz/Cargo.toml` |

There is one crate in the workspace. `Cargo.lock` pins 75 packages, all
transitive dev-dependency closure of `criterion`, `rand`, and `libfuzzer-sys`.

## 3. Module and file layout

```
DataKit/
├── src/
│   └── lib.rs                  # entire crate: 2 public types + 4 unit tests
├── tests/
│   ├── pipeline_test.rs        # 5 integration tests (public API only)
│   ├── integration/README.md   # placeholder, empty suite
│   └── e2e/README.md           # placeholder, empty suite
├── benches/
│   └── criterion_bench.rs      # [[bench]] harness = false
├── fuzz/
│   ├── Cargo.toml
│   └── fuzz_target.rs          # libfuzzer-sys target, invariant checks
├── scripts/
│   └── scorecard_ci.py         # 88-pillar repository scorecard
└── docs/
    ├── ARCHITECTURE.md         # this file
    └── API_REFERENCE.md
```

There are no submodules. `src/lib.rs` is the crate root and the only source
file. No `mod` declarations exist.

## 4. Implemented layers

The implemented design is two layers, both in-memory and synchronous.

### 4.1 Data layer: `DataStream<T>`

A transparent wrapper around a value of type `T`. It is the unit of data that
flows through a pipeline. It carries no metadata, no timestamp, no schema, no
provenance. It derives `Debug`, `Clone`, `PartialEq`, `Eq`.

```
DataStream<T> { pub data: T }
```

Because `data` is a public field, construction is possible both via
`DataStream::new` and via struct literal.

### 4.2 Processing layer: `Pipeline<T, U>`

Holds a single boxed closure and maps it across a batch.

```
Pipeline<T, U> { transform: Box<dyn Fn(T) -> U> }

run(input: Vec<DataStream<T>>) -> Vec<DataStream<U>>
```

Properties grounded in the source:

- The transform is **infallible**: the closure signature is `Fn(T) -> U`, so a
  pipeline cannot produce an error and there is no `Result` path anywhere.
- The transform is `Fn`, not `FnMut` or `FnOnce`, so it cannot carry mutable
  state across elements without interior mutability.
- `run` takes `Vec` by value and consumes it; it returns a new `Vec`. It is
  strictly batch, not streaming, not lazy.
- There are no `Send`/`Sync` bounds on `T`, `U`, or the closure, so `Pipeline`
  is not `Send` unless the closure happens to be.
- `Pipeline` does not implement `Clone`, `Debug`, or any trait.

### 4.3 Data flow

```
Vec<DataStream<T>>  --into_iter-->  (transform)(stream.data)  -->  Vec<DataStream<U>>
```

Each input element is transformed exactly once, in order, preserving length.
The fuzz target asserts exactly this: `output.len() == input.len()` and each
element equals the applied transform.

## 5. Cross-cutting concerns

| Concern | Implementation |
|---|---|
| Error handling | None. No `Result`, no `Error` type, no `panic!` in library code. |
| Concurrency | None. No threads, channels, async, or `rayon`. |
| I/O | None. No filesystem, network, database, or serialization. |
| Serialization | None. No `serde` derive on either type. |
| Config / credentials | None in this crate. `CONTRIBUTING.md` mentions a local `~/.datakit/credentials` store that is not implemented here. |
| Telemetry / logging | None. |
| Feature flags | None in `Cargo.toml`. |

## 6. Implemented versus planned

The original README promised a unified ETL framework. The table records what is
actually present, so that the gap is explicit and not mistaken for
documentation debt.

| Roadmap item | Implemented? | Evidence |
|---|---|---|
| Type-safe transformations | Partial | `Pipeline<T, U>` is typed, but infallible and batch-only. |
| Streaming data pipelines | No | `run` consumes a `Vec`; no iterator/stream abstraction. |
| Multi-backend support (files, DB, API, MQ) | No | No dependency or trait for any backend. |
| Plugin architecture for custom connectors | No | No registry, trait, or dynamic loading. |
| Source/sink abstractions | No | Only `DataStream` and `Pipeline` exist. |

## 7. Testing architecture

| Layer | Location | Count | Asserts |
|---|---|---|---|
| Unit | `src/lib.rs` `#[cfg(test)]` | 4 | construction, empty input, identity, composition |
| Integration | `tests/pipeline_test.rs` | 5 | basic transform, type conversion, string transform, single element, large batch |
| Doc test | `src/lib.rs` doc comment | 1 | README-equivalent double example |
| Fuzz | `fuzz/fuzz_target.rs` | 1 target | length preservation, per-element correctness |
| Bench | `benches/criterion_bench.rs` | 2 groups | `pipeline_run` at sizes 10/100/1000, `datastream_new` |

`tests/integration/` and `tests/e2e/` contain only placeholder READMEs and
contribute no tests. All 10 real tests pass (`cargo test --all`, verified
2026-09-17).

## 8. Extension points, if this were revived

Recorded for completeness; not implemented and not planned, since the
repository is deprecated.

1. Fallible transforms would require changing `Box<dyn Fn(T) -> U>` to
   `Box<dyn Fn(T) -> Result<U, E>>` and `run` to return a `Result`.
2. Streaming would require a `run_iter` taking `IntoIterator` and returning an
   iterator rather than `Vec`.
3. Sources and sinks would add `Source<T>` and `Sink<U>` traits around the
   existing `Pipeline`.

## 9. Related documents

- [../README.md](../README.md) for status and quickstart
- [API_REFERENCE.md](API_REFERENCE.md) for exact signatures
- [../TOMBSTONE.md](../TOMBSTONE.md) for the deprecation record
- [../CONTRIBUTING.md](../CONTRIBUTING.md) for the contributor contract
