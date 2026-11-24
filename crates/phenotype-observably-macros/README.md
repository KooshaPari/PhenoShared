# phenotype-observably-macros

Procedural macros for PhenoObservability instrumentation.

> **Provenance.** The original crate lived at
> `PhenoObservability/crates/phenotype-observably-macros`, outside this
> repository. That project is unreachable, so the original source could not be
> recovered. This implementation was reconstructed from an in-flight PR branch
> (`chore/remove-dead-integration-crate`) that carried a real
> `tracing::Instrument`-based implementation of the same package, then
> corrected — see [Deviations](#deviations-from-the-pr-branch-implementation)
> for what changed and why. This is **not** a verbatim upstream copy.

Replaces the previous pass-through stand-in, which accepted
`#[async_instrumented]` and returned the annotated item unchanged — so 44 call
sites compiled while emitting no spans at all.

## Macros

### `#[async_instrumented]`

Wraps an `async fn` body in a `tracing` span that stays entered across every
`.await` point in the body.

| Option            | Meaning                                                 |
|-------------------|---------------------------------------------------------|
| `name = "..."`    | span name (defaults to the function ident)              |
| `level = "..."`   | `trace` / `debug` / `info` (default) / `warn` / `error` |
| `skip(a, b, ...)` | function arguments to omit from the span field list     |

```rust
use phenotype_observably_macros::async_instrumented;

#[async_instrumented]
async fn fetch(url: &str) -> anyhow::Result<String> {
    // span `fetch` is entered across every await below
    reqwest::get(url).await?.text().await
}

#[async_instrumented(level = "warn", name = "ingest", skip(secret))]
async fn ingest(secret: &str, payload: Vec<u8>) -> Result<(), Error> {
    Ok(())
}
```

Fields for non-skipped arguments are declared as `tracing::field::Empty`, which
matches `tracing::instrument`: the field names appear on the span but carry no
value unless the body records them. `self` receivers are never added as fields.

**Supported function shapes.** The public signature is preserved verbatim and
only the body is wrapped, so the macro works with:

- `&self` and `&mut self` methods
- generic functions and explicit `where` clauses
- any return type, including `Result` aliases and `impl Trait`
- reference arguments with elided lifetimes

**Sync functions** are passed through unchanged, as are `const fn` and anything
else that is not `async`.

**Feature gate.** The `tracing` feature is on by default and is read by the
macro at expansion time, so the emitted code is always one definite variant.

## Deviations from the PR-branch implementation

Two defects were found and fixed before adopting it:

1. **`&self` did not compile.** That version rewrote the signature to drop
   `async` and return `impl Future<Output = T> + 'fn_lifetime`, injecting a
   synthetic lifetime and rewriting anonymous `&T` argument lifetimes to match.
   It only handled `syn::FnArg::Typed`, so `&self` kept its own elided lifetime
   while the return type claimed `'fn_lifetime`, failing with
   `lifetime may not live long enough` on real call sites (2 of 3 `&self`
   methods in `focus-always-on`). Instrumenting the body instead leaves the
   signature untouched and sidesteps the whole problem.
2. **The feature gate was emitted, not evaluated.** It wrote
   `#[cfg(feature = "tracing")]` / `#[cfg(not(feature = "tracing"))]` into the
   *consumer*, where the cfg resolves against that crate's features. Only 2 of
   12 dependents declare such a feature and neither enables it by default, so
   the macro would have silently expanded to the pass-through branch —
   reproducing the silent no-op it was meant to remove.

## Tests

- `tests/integration.rs` — intrinsic guarantees: span emitted on entry, custom
  level honoured, `skip(...)` suppresses fields, return values preserved, sync
  passthrough.
- `tests/consumer_instrumentation.rs` — consumer-shaped usage across a repo
  loader, an HTTP client, and a queue worker, asserting spans are observable
  from a `tracing` `Layer`.

```bash
cargo test -p phenotype-observably-macros
```

## License

MIT OR Apache-2.0.
