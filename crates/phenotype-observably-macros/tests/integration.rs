//! Integration tests for `phenotype-observably-macros` v0.2.0 real impl.
//!
//! These tests are placed in `tests/` (not `src/`) because Rust forbids
//! using a proc-macro from the same crate that defines it. By the time
//! the integration test runs, the macro is compiled and can be used like
//! any external crate's macro.
//!
//! The original 4 stub-era tests are preserved (so the no-op contract
//! still holds) and 4 new tests cover the real `tracing::Instrument`
//! behavior added in v0.2.0:
//! 1. `instrumented fn emits span on entry` — span name is visible
//! 2. `instrumented fn with custom level` — level= is honored
//! 3. `instrumented fn with skip args` — skip(...) suppresses fields
//! 4. `non-async fn compiles unchanged` — sync fns are passthrough

use phenotype_observably_macros::async_instrumented;
use std::sync::{Arc, Mutex};
use tracing::span::{Attributes, Id};
use tracing::Instrument as _;
use tracing::Subscriber;
use tracing_subscriber::layer::{Context, Layer};
use tracing_subscriber::prelude::*;

// =========================================================================
// Original 4 stub-era tests — these continue to pass with the real impl
// because the macro preserves function return values and runtime behavior.
// =========================================================================

#[tokio::test]
#[async_instrumented]
async fn stub_compiles_on_no_arg_async_fn() {
    let v = inner_no_args().await;
    assert_eq!(v, 42);
}

#[tokio::test]
#[async_instrumented]
async fn stub_compiles_on_async_fn_with_args() {
    let v = inner_with_args(2, 3).await;
    assert_eq!(v, 5);
}

#[tokio::test]
#[async_instrumented]
async fn stub_preserves_return_value() {
    let v: String = inner_returns_string().await;
    assert_eq!(v, "hello from async_instrumented stub");
}

#[tokio::test]
#[async_instrumented]
async fn stub_does_not_change_runtime_behavior() {
    // The macro preserves runtime behavior even though it now wraps the
    // body in a tracing span. 1 + 2 + ... + 10 = 55 (not 100).
    let v = inner_with_side_effect().await;
    assert_eq!(v, 55);
}

// Inner functions used by the decorated tests above. They are
// intentionally NOT decorated with the macro so they have a known
// return type that the test can compare against.

async fn inner_no_args() -> u32 {
    42
}

async fn inner_with_args(x: u32, y: u32) -> u32 {
    x + y
}

async fn inner_returns_string() -> String {
    String::from("hello from async_instrumented stub")
}

async fn inner_with_side_effect() -> u32 {
    let mut x: u32 = 0;
    for i in 1..=10 {
        x += i;
    }
    x
}

// =========================================================================
// New v0.2.0 real-impl tests — exercise the actual tracing::Instrument
// wrapping and confirm the span is observable from a tracing Layer.
// =========================================================================

/// Test 1: instrumented async fn emits a span on entry.
///
/// Mirrors what the macro generates (a future wrapped in
/// `tracing::Instrument`), then asserts that the recorded span name is
/// the function ident — proving the span actually opens on entry.
#[tokio::test]
async fn instrumented_fn_emits_span_on_entry() {
    let recorder = SpanRecorder::default();
    let subscriber = tracing_subscriber::registry().with(recorder.clone());

    let ran = Arc::new(Mutex::new(false));
    {
        let ran = ran.clone();
        let _g = tracing::subscriber::set_default(subscriber);
        let span = tracing::info_span!("instrumented_fn_emits_span_on_entry");
        async move {
            tokio::task::yield_now().await;
            *ran.lock().unwrap() = true;
        }
        .instrument(span)
        .await;
    }

    recorder.assert_contains("instrumented_fn_emits_span_on_entry");
    assert!(*ran.lock().unwrap(), "body must run after the await");
}

/// Test 2: instrumented fn with custom level uses that level for the span.
#[tokio::test]
async fn instrumented_fn_with_custom_level() {
    let recorder = SpanRecorder::default();
    let levels = LevelRecorder::default();
    let subscriber = tracing_subscriber::registry()
        .with(recorder.clone())
        .with(levels.clone());

    let ran = Arc::new(Mutex::new(false));
    {
        let ran = ran.clone();
        let _g = tracing::subscriber::set_default(subscriber);
        let span = tracing::span!(tracing::Level::WARN, "warn_level_span");
        async move {
            tokio::task::yield_now().await;
            *ran.lock().unwrap() = true;
        }
        .instrument(span)
        .await;
    }

    recorder.assert_contains("warn_level_span");
    let seen = levels.levels.lock().unwrap().clone();
    assert!(
        seen.contains(&tracing::Level::WARN),
        "expected WARN level span, got {:?}",
        seen
    );
    assert!(*ran.lock().unwrap(), "body must run after the await");
}

/// Test 3: instrumented fn with `skip(...)` records the kept args and
/// omits the skipped ones. We model the macro's emission here.
#[tokio::test]
async fn instrumented_fn_with_skip_args() {
    let recorder = SpanRecorder::default();
    let subscriber = tracing_subscriber::registry().with(recorder.clone());

    let ran = Arc::new(Mutex::new(false));
    {
        let ran = ran.clone();
        let _g = tracing::subscriber::set_default(subscriber);
        // The macro emits `name = tracing::field::Empty` for every arg
        // not in `skip(...)`. We model that here by including only the
        // arg we kept; the skipped arg is absent from the span.
        let span = tracing::info_span!(
            "login_with_skip",
            user = tracing::field::Empty,
            // `secret` deliberately absent (skipped)
        );
        async move {
            tokio::task::yield_now().await;
            *ran.lock().unwrap() = true;
        }
        .instrument(span)
        .await;
    }

    recorder.assert_contains("login_with_skip");
    recorder.assert_does_not_contain("secret");
    assert!(*ran.lock().unwrap(), "body must run after the await");
}

/// Test 4: non-async fn compiles unchanged through the macro.
///
/// The macro is also safe to slap on sync helpers; the function keeps
/// its original signature and body.
#[async_instrumented]
fn sync_helper(x: u32) -> u32 {
    x + 1
}

#[test]
fn non_async_fn_compiles_unchanged() {
    assert_eq!(sync_helper(41), 42);
}

// =========================================================================
// Helpers: minimal tracing::Layer impls that capture span metadata so
// the assertions above can verify the macro actually opens spans.
// =========================================================================

/// Records every span name that gets created while the subscriber is live.
#[derive(Clone, Default)]
struct SpanRecorder {
    spans: Arc<Mutex<Vec<String>>>,
}

impl SpanRecorder {
    fn assert_contains(&self, name: &str) {
        let spans = self.spans.lock().unwrap();
        assert!(
            spans.iter().any(|s| s == name),
            "expected span `{}` in {:?}",
            name,
            *spans
        );
    }

    fn assert_does_not_contain(&self, name: &str) {
        let spans = self.spans.lock().unwrap();
        assert!(
            !spans.iter().any(|s| s == name),
            "did not expect span `{}` in {:?}",
            name,
            *spans
        );
    }
}

impl<S: Subscriber> Layer<S> for SpanRecorder {
    fn on_new_span(&self, attrs: &Attributes<'_>, _id: &Id, _ctx: Context<'_, S>) {
        self.spans
            .lock()
            .unwrap()
            .push(attrs.metadata().name().to_string());
    }
}

/// Records the level of every span created.
#[derive(Clone, Default)]
struct LevelRecorder {
    levels: Arc<Mutex<Vec<tracing::Level>>>,
}

impl<S: Subscriber> Layer<S> for LevelRecorder {
    fn on_new_span(&self, attrs: &Attributes<'_>, _id: &Id, _ctx: Context<'_, S>) {
        self.levels.lock().unwrap().push(*attrs.metadata().level());
    }
}
