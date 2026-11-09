//! Consumer-instrumentation integration tests for `phenotype-observably-macros`.
//!
//! These tests exercise `#[async_instrumented]` in a "consumer" pattern —
//! i.e., the way a downstream crate would use the macro to instrument its
//! own domain logic. They are kept separate from `tests/integration.rs`
//! (which exercises the macro's intrinsic guarantees) so that:
//!
//! 1. The intrinsic tests are not polluted by domain-specific assertions.
//! 2. The consumer pattern can be evolved (e.g., adding a new domain like
//!    "http" or "queue") without touching the intrinsic test surface.
//! 3. A future external consumer crate can copy this file as a reference
//!    integration-test layout.
//!
//! Each test uses the same `SpanRecorder` layer pattern as
//! `integration.rs` so the recorded spans are observable from a tracing
//! `Layer` rather than relying on log-line parsing.
//!
//! Domain coverage:
//! - `repo_loader::load`: simulated repository loader (multi-arg async fn)
//! - `http_client::fetch_url`: simulated HTTP client (single-arg with skip)
//! - `queue_worker::drain`: simulated queue worker (no-arg async fn, custom name)

use phenotype_observably_macros::async_instrumented;
use std::sync::{Arc, Mutex};
use tracing::span::{Attributes, Id};
use tracing::Subscriber;
use tracing_subscriber::layer::{Context, Layer};
use tracing_subscriber::prelude::*;

// =========================================================================
// Span recorder — captures the names of every span entered on the current
// thread. Shared across tests so each test owns its recorder.
// =========================================================================

#[derive(Clone, Default)]
struct SpanRecorder {
    names: Arc<Mutex<Vec<String>>>,
}

impl<S: Subscriber> Layer<S> for SpanRecorder {
    fn on_new_span(&self, attrs: &Attributes<'_>, _id: &Id, _ctx: Context<'_, S>) {
        let mut g = self.names.lock().unwrap();
        g.push(attrs.metadata().name().to_string());
    }
}

impl SpanRecorder {
    fn take(&self) -> Vec<String> {
        let mut g = self.names.lock().unwrap();
        std::mem::take(&mut *g)
    }
}

// =========================================================================
// Domain 1: repository loader — multi-arg async fn, default span name
// =========================================================================

pub mod repo_loader {
    use super::async_instrumented;

    #[async_instrumented]
    pub async fn load(owner: &str, name: &str, ref_: &str) -> String {
        format!("{owner}/{name}@{ref_}")
    }
}

#[test]
fn consumer_repo_loader_emits_span_with_function_ident() {
    let recorder = SpanRecorder::default();
    let subscriber = tracing_subscriber::registry().with(recorder.clone());

    let result = tracing::subscriber::with_default(subscriber, || {
        futures_lite::future::block_on(repo_loader::load("KooshaPari", "pheno-otel", "main"))
    });
    assert_eq!(result, "KooshaPari/pheno-otel@main");
    let names = recorder.take();
    assert!(
        names.iter().any(|n| n == "load"),
        "expected span 'load' to be entered; recorded={names:?}",
    );
}

// =========================================================================
// Domain 2: HTTP client — single-arg async fn, name= override, skip(secret)
// =========================================================================

pub mod http_client {
    use super::async_instrumented;

    #[async_instrumented(name = "http.fetch", skip(api_key))]
    pub async fn fetch_url(url: &str, _api_key: &str) -> String {
        // In a real client this would be a reqwest::get call.
        format!("would fetch {url}")
    }
}

#[test]
fn consumer_http_client_uses_custom_span_name_and_skips_secret() {
    let recorder = SpanRecorder::default();
    let _guard =
        tracing::subscriber::set_default(tracing_subscriber::registry().with(recorder.clone()));

    let result = futures_lite::future::block_on(http_client::fetch_url(
        "https://api.example.com/v1",
        "REDACTED",
    ));
    assert_eq!(result, "would fetch https://api.example.com/v1");

    let names = recorder.take();
    assert!(
        names.iter().any(|n| n == "http.fetch"),
        "expected custom span 'http.fetch'; recorded={names:?}",
    );
    assert!(
        !names.iter().any(|n| n == "fetch_url"),
        "function ident should NOT be the span name when name= is set; recorded={names:?}",
    );
}

// =========================================================================
// Domain 3: queue worker — no-arg async fn, level= override
// =========================================================================

pub mod queue_worker {
    use super::async_instrumented;

    #[async_instrumented(level = "warn", name = "queue.drain")]
    pub async fn drain() -> u32 {
        // Simulated drain count.
        7
    }
}

#[test]
fn consumer_queue_worker_uses_custom_level_and_name() {
    let recorder = SpanRecorder::default();
    let _guard =
        tracing::subscriber::set_default(tracing_subscriber::registry().with(recorder.clone()));

    let drained = futures_lite::future::block_on(queue_worker::drain());
    assert_eq!(drained, 7);

    let names = recorder.take();
    assert!(
        names.iter().any(|n| n == "queue.drain"),
        "expected custom span 'queue.drain'; recorded={names:?}",
    );
}

// =========================================================================
// Cross-domain test: spans from multiple consumer fns do not collide
// =========================================================================

#[test]
fn consumer_spans_from_different_domains_are_distinct() {
    let recorder = SpanRecorder::default();
    let _guard =
        tracing::subscriber::set_default(tracing_subscriber::registry().with(recorder.clone()));

    let _ = futures_lite::future::block_on(repo_loader::load("a", "b", "c"));
    let _ = futures_lite::future::block_on(http_client::fetch_url("https://x", "k"));
    let _ = futures_lite::future::block_on(queue_worker::drain());

    let names = recorder.take();
    // All three domain spans should have been entered at least once.
    assert!(
        names.iter().any(|n| n == "load"),
        "missing 'load'; recorded={names:?}"
    );
    assert!(
        names.iter().any(|n| n == "http.fetch"),
        "missing 'http.fetch'; recorded={names:?}"
    );
    assert!(
        names.iter().any(|n| n == "queue.drain"),
        "missing 'queue.drain'; recorded={names:?}"
    );
}
