# phenotype-observably-macros Usage Guide

Adoption lessons from FocalPoint crates (W-72/73/75/76).

## What Works

### Inherent Async Functions (Result Variants)

Any async fn returning `Result<T, E>` automatically instruments:

```rust
use phenotype_observably_macros::async_instrumented;

#[async_instrumented]
pub async fn process_event(id: &str) -> Result<String, CustomError> {
    // Span created with function name, errors logged at warn level
    Ok(format!("Processed {}", id))
}
```

### `anyhow::Result<T>` (Recommended)

Simpler error handling; macro fully supports:

```rust
use phenotype_observably_macros::async_instrumented;

#[async_instrumented]
pub async fn fetch_data() -> anyhow::Result<Vec<u8>> {
    let data = expensive_operation().await?;
    Ok(data)
}
```

### Custom Result Aliases

Use your own `type MyResult<T> = Result<T, MyError>`:

```rust
pub type MyResult<T> = Result<T, Box<dyn std::error::Error>>;

#[async_instrumented]
pub async fn do_work() -> MyResult<()> {
    Ok(())
}
```

## What Does NOT Work

### Trait Methods (with `async_trait`)

```rust
// ❌ BROKEN — Send violation in async_trait + macro combo
#[async_trait]
impl MyTrait for MyStruct {
    #[async_instrumented]
    async fn method(&self) -> anyhow::Result<()> {
        // ERROR: span guard is !Send, breaks async_trait Future
    }
}
```

**Workaround:** Inner function pattern
```rust
#[async_trait]
impl MyTrait for MyStruct {
    async fn method(&self) -> anyhow::Result<()> {
        self._method_impl().await
    }
}

impl MyStruct {
    #[async_instrumented]
    async fn _method_impl(&self) -> anyhow::Result<()> {
        // Safe — not in trait impl
    }
}
```

### Non-Result Returns

```rust
// ❌ FAILS — macro expects Result-like return
#[async_instrumented]
pub async fn get_count() -> usize {
    42
}

// ❌ FAILS — bool not supported
#[async_instrumented]
pub async fn is_valid() -> bool {
    true
}
```

**Workaround:** Wrap in `anyhow::Result`
```rust
#[async_instrumented]
pub async fn get_count() -> anyhow::Result<usize> {
    Ok(42)
}
```

### Length/Predicate Helpers

```rust
// ❌ NO — don't use on is_empty, len, or similar
#[async_instrumented]
pub async fn is_empty(&self) -> bool { ... }
```

These methods return `bool` (not Result) and don't benefit from result logging.

## Dependency Path Setup

When consuming in another crate, the path dependency must traverse up 3 levels from your crate to reach `PhenoObservability`:

```toml
# In FocalPoint/crates/focus-eval/Cargo.toml
[dependencies]
phenotype-observably-macros = { path = "../../../PhenoObservability/crates/phenotype-observably-macros" }
```

From `focus-eval/src`:
- `../` → focus-eval root
- `../../` → crates/ dir
- `../../../` → FocalPoint root
- `../../../PhenoObservability/crates/phenotype-observably-macros/` → target

## Send Safety (W-75 Fix)

The macro now safely drops the span guard before awaiting to prevent Send violations:

```rust
// Internal implementation (safe for !Send guards)
let _guard = tracing::debug_span!("fn_name").entered();
drop(_guard);  // ← Critical: released before await
let result = async { block }.await;
```

This allows the macro to work with tracing::Instrument and async contexts.

## Real-World Examples

### focus-eval (Result<T, E>)
```rust
#[async_instrumented]
pub async fn tick(&self, now: DateTime<Utc>) -> anyhow::Result<EvaluationReport> {
    let cursor = self.cursor_store.get_cursor(...).await?;
    // ... evaluation logic ...
    Ok(report)
}
```

### focus-rituals (anyhow::Result<T>)
```rust
#[async_instrumented]
pub async fn generate_weekly_review(&self, now: DateTime<Utc>) -> anyhow::Result<WeeklyReview> {
    let week_starting = week_start(now.date_naive());
    // ... ritual logic ...
    Ok(review)
}
```

## When Not to Use

- **Pure data reads** returning non-Result (use `#[tracing::instrument]` instead)
- **Trait methods** (use inner function pattern)
- **Synchronous code** (no macro needed; use `#[tracing::instrument]`)

For these, fall back to manual `#[tracing::instrument(skip_all)]`.

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| "expected `Result`" | Return type not recognized | Use `anyhow::Result<T>` or explicit `Result<T, E>` |
| "Future is not `Send`" | Trait method with async_trait | Use inner function pattern |
| Span not appearing | Tracing subscriber not initialized | Initialize `tracing-subscriber` in main |
| Errors not logged | Custom error type has poor Display | Implement `Display` or `Error` traits |

## See Also

- `README.md` — Macro overview
- `src/lib.rs` — Implementation details
- [tracing docs](https://docs.rs/tracing/)
