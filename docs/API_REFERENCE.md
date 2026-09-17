# DataKit API Reference

> Status: **DEPRECATED** as of 2026-09-17. Superseded by
> `phenotype-python-sdk/packages/data-kit`. See
> [../TOMBSTONE.md](../TOMBSTONE.md).

Crate `datakit` v0.1.0, edition 2021. This is the complete public API. Every
signature below is copied from `src/lib.rs`; there is nothing else exported.

## Public API surface (complete)

| Item | Kind | File |
|---|---|---|
| `DataStream<T>` | struct | `src/lib.rs` |
| `DataStream::<T>::new` | fn | `src/lib.rs` |
| `DataStream::<T>::data` | pub field | `src/lib.rs` |
| `Pipeline<T, U>` | struct | `src/lib.rs` |
| `Pipeline::<T, U>::new` | fn | `src/lib.rs` |
| `Pipeline::<T, U>::run` | fn | `src/lib.rs` |

No traits, no macros, no functions, no constants, no type aliases, no modules,
no re-exports beyond these six items.

## `DataStream<T>`

A single data record flowing through a pipeline. Wraps a value of type `T`, the
core data unit that sources emit, transforms process, and sinks consume.

```rust
pub struct DataStream<T> {
    pub data: T,
}

impl<T> DataStream<T> {
    pub fn new(data: T) -> Self;
}
```

### Derives and trait implementations

| Trait | Derived / implemented |
|---|---|
| `Debug` | derived |
| `Clone` | derived |
| `PartialEq` | derived |
| `Eq` | derived |
| `Default` | not implemented |
| `Hash`, `Ord` | not implemented |
| `serde::Serialize` / `Deserialize` | not implemented |

Note: `Eq` is derived unconditionally, so `DataStream<T>: Eq` holds only when
`T: Eq` (standard derive bounds).

### `DataStream::new`

| | |
|---|---|
| Signature | `pub fn new(data: T) -> Self` |
| Input | `data: T`, the wrapped value |
| Output | `DataStream<T>` containing `data` |
| Errors | none |
| Panics | none |

Because `data` is a public field, `DataStream::new(x)` and
`DataStream { data: x }` are equivalent constructions.

### Example

```rust
use datakit::DataStream;

let stream = DataStream::new(42);
assert_eq!(stream.data, 42);
```

## `Pipeline<T, U>`

A type-safe entrypoint for a data pipeline. A pipeline accepts a vector of
`DataStream<T>` inputs, applies a transformation, and produces
`DataStream<U>` outputs.

```rust
pub struct Pipeline<T, U> {
    transform: Box<dyn Fn(T) -> U>,
}

impl<T, U> Pipeline<T, U> {
    pub fn new(transform: Box<dyn Fn(T) -> U>) -> Self;
    pub fn run(&self, input: Vec<DataStream<T>>) -> Vec<DataStream<U>>;
}
```

The `transform` field is private. `Pipeline` implements no public traits.

### Type parameters

| Parameter | Role | Bounds |
|---|---|---|
| `T` | input element type | none |
| `U` | output element type | none |

There are no `Sized`, `Send`, `Sync`, `'static`, or lifetime bounds on `T`, `U`,
or the closure. Consequently `Pipeline<T, U>` is `Send`/`Sync` only if the boxed
closure is.

### `Pipeline::new`

| | |
|---|---|
| Signature | `pub fn new(transform: Box<dyn Fn(T) -> U>) -> Self` |
| Input | a boxed, infallible, callable-by-`&self` transform |
| Output | `Pipeline<T, U>` owning the transform |
| Errors | none |
| Panics | none |

The closure type is `Fn`, not `FnMut` or `FnOnce`. A transform that needs to
mutate state across calls must use interior mutability.

### `Pipeline::run`

| | |
|---|---|
| Signature | `pub fn run(&self, input: Vec<DataStream<T>>) -> Vec<DataStream<U>>` |
| Input | a `Vec<DataStream<T>>`, consumed by value |
| Output | a new, equal-length `Vec<DataStream<U>>`, order preserved |
| Errors | none; the transform is infallible |
| Panics | only if the caller's closure panics |

Contract, as asserted by the fuzz target and integration tests:

1. `output.len() == input.len()` for all inputs, including the empty `Vec`.
2. `output[i].data == (transform)(input[i].data)` for every `i`.
3. Ordering is preserved; the implementation is a sequential `into_iter().map()`.
4. `run` takes `&self`, so the same pipeline can be reused across batches.

### Example (doc test in `src/lib.rs`, verified by `cargo test`)

```rust
use datakit::{DataStream, Pipeline};

let double = Pipeline::new(Box::new(|x: i32| x * 2));
let input  = vec![DataStream::new(1), DataStream::new(2)];
let output = double.run(input);
assert_eq!(output, vec![DataStream::new(2), DataStream::new(4)]);
```

### Composition example

`Pipeline` has no combinator methods. Composition is done by manually chaining
`run` calls:

```rust
use datakit::{DataStream, Pipeline};

let double  = Pipeline::new(Box::new(|x: i32| x * 2));
let add_one = Pipeline::new(Box::new(|x: i32| x + 1));

let input  = vec![DataStream::new(1), DataStream::new(2), DataStream::new(3)];
let output = add_one.run(double.run(input)); // (x * 2) + 1

assert_eq!(output, vec![DataStream::new(3), DataStream::new(5), DataStream::new(7)]);
```

### Type-changing pipelines

`T` and `U` may differ, which is the crate's "type-safe transformation" claim:

```rust
use datakit::{DataStream, Pipeline};

let to_len = Pipeline::new(Box::new(|s: String| s.len()));
let output = to_len.run(vec![DataStream::new("hello".to_string())]);

assert_eq!(output, vec![DataStream::new(5usize)]);
```

## Semantics and limitations

| Aspect | Behavior |
|---|---|
| Execution model | synchronous, eager, batch over `Vec` |
| Laziness | none; input is fully consumed and output fully materialized |
| Streaming / backpressure | not supported |
| Concurrency | none; no `rayon`, threads, or async |
| Error propagation | impossible; no `Result` in the public API |
| Serialization | none; neither type implements `serde` traits |
| I/O | none; no files, network, DB, or message queue access |
| Metadata | none; `DataStream` wraps a bare value with no schema or timestamp |

## Related documents

- [../README.md](../README.md) for status and quickstart
- [ARCHITECTURE.md](ARCHITECTURE.md) for the layer breakdown
- [../TOMBSTONE.md](../TOMBSTONE.md) for the deprecation record
