//! Tiny Axum server exposing `/metrics` and `/health` endpoints.
//!
//! Usage:
//!
//! ```sh
//! cargo run -p pareto-rs --bin pareto-server
//! # Then visit http://localhost:9090/health
//! #          or http://localhost:9090/metrics
//! ```

use axum::Router;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use std::net::SocketAddr;
use std::sync::Arc;

use pareto_rs::metrics::ParetoMetrics;

/// Application state shared across handlers.
struct AppState {
    metrics: ParetoMetrics,
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

/// `GET /health` — liveness / readiness probe.
async fn health() -> Response {
    (StatusCode::OK, "ok\n").into_response()
}

/// `GET /metrics` — Prometheus-compatible text exposition.
async fn metrics_endpoint(
    axum::extract::State(state): axum::extract::State<Arc<AppState>>,
) -> Response {
    let body = state.metrics.encode_metrics();
    (
        StatusCode::OK,
        [("content-type", "text/plain; version=0.0.4; charset=utf-8")],
        body,
    )
        .into_response()
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    let state = Arc::new(AppState {
        metrics: ParetoMetrics::new(),
    });

    let app = Router::new()
        .route("/health", get(health))
        .route("/metrics", get(metrics_endpoint))
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 9090));
    println!("pareto-server listening on {addr}");

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .expect("failed to bind");
    axum::serve(listener, app).await.expect("server error");
}
