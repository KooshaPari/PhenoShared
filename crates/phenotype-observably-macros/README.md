# phenotype-observably-macros (vendored)

> **Vendored from PhenoObservability** commit `62ff523e`
> ("feat: absorb pheno-tracing into PhenoObservability workspace (ADR-036)").
> Original source: <https://github.com/KooshaPari/PhenoObservability>.
> License: MIT OR Apache-2.0 (dual-licensed upstream; preserved verbatim).

This crate is a verbatim copy of the upstream macro. It is pinned here to
unblock the PhenoShared workspace build, which previously declared a path-dep
into the now-private `PhenoObservability` repo (`../../../PhenoObservability/...`)
that single-repo CI could not resolve.

When upstream re-publishes or `PhenoObservability` becomes public again, this
crate can be replaced with a registry dep in one PR.

# phenotype-observably-macros

Procedural macros for PhenoObservability instrumentation patterns.

## Macros

### `#[async_instrumented]`

Automatically instrument async functions with:
- Tracing span entry/exit with function name
- Result logging (debug on success, warn on error)
- Works with any Result-like return type (`Result<T, E>`, `anyhow::Result<T>`, custom aliases)

**Compatible functions:**
- Async functions with Result returns
- Inherent methods (not trait methods via `async_trait`)
- Generic functions with type parameters

**Incompatible patterns:**
- Trait methods (use inner function pattern instead)
- Non-Result returns (`-> bool`, `-> String`, etc.)
- Synchronous functions

### `pii_scrub`

Mark fields that should scrub PII from logs. Converts values to `***[n]` (length-only format).

```rust
let email = pii_scrub("user@example.com");
tracing::info!(email = %email, "user action");
// Output: email = ***[19]
```

## Usage Examples

See `USAGE.md` for comprehensive adoption patterns, workarounds, and real examples from FocalPoint.

## See Also

- `USAGE.md` — Complete adoption guide with patterns and workarounds
- `../focus-eval` — `Result<T, E>` variant example
- `../focus-rituals` — `anyhow::Result<T>` variant example
