//! Prometheus metrics facade for `phenotype-tooling-observability`.
//!
//! Provides a lazy-init global [`prometheus::Registry`] plus default
//! counters/histograms covering CLI invocation, errors, and duration.
//!
//! When the `server` feature is enabled, [`serve`] starts an axum HTTP
//! server exposing `/metrics` (Prometheus text format).
//!
//! ## Example
//!
//! ```rust,no_run
//! # #[cfg(feature = "server")]
//! # async fn ex() -> Result<(), phenotype_tooling_observability::Error> {
//! use phenotype_tooling_observability::metrics;
//! metrics::inc_invocation();
//! metrics::observe_duration(std::time::Duration::from_millis(42));
//! let addr: std::net::SocketAddr = "0.0.0.0:9090".parse().unwrap();
//! metrics::serve(addr).await?;
//! # Ok(()) }
//! ```

use once_cell::sync::Lazy;
use prometheus::{
    register_histogram_with_registry, register_int_counter_with_registry, Encoder, Histogram,
    IntCounter, Registry, TextEncoder,
};

/// Process-global Prometheus registry.
pub static REGISTRY: Lazy<Registry> = Lazy::new(Registry::new);

/// `cli_invocations_total{cmd}` — number of times each CLI subcommand ran.
pub static INVOCATIONS: Lazy<IntCounter> = Lazy::new(|| {
    register_int_counter_with_registry!(
        "cli_invocations_total",
        "Total number of CLI invocations",
        REGISTRY
    )
    .expect("register cli_invocations_total")
});

/// `cli_errors_total{cmd}` — number of times each CLI subcommand errored.
pub static ERRORS: Lazy<IntCounter> = Lazy::new(|| {
    register_int_counter_with_registry!("cli_errors_total", "Total number of CLI errors", REGISTRY)
        .expect("register cli_errors_total")
});

/// `cli_duration_seconds` — histogram of CLI invocation latency.
pub static DURATION: Lazy<Histogram> = Lazy::new(|| {
    register_histogram_with_registry!(
        "cli_duration_seconds",
        "CLI invocation duration in seconds",
        vec![0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        REGISTRY
    )
    .expect("register cli_duration_seconds")
});

/// Increment the global invocations counter.
pub fn inc_invocation() {
    INVOCATIONS.inc();
}

/// Increment the global errors counter.
pub fn inc_error() {
    ERRORS.inc();
}

/// Observe a CLI invocation duration in seconds.
pub fn observe_duration(d: std::time::Duration) {
    DURATION.observe(d.as_secs_f64());
}

/// Render the current registry as Prometheus text-format bytes.
pub fn render() -> Result<Vec<u8>, prometheus::Error> {
    let encoder = TextEncoder::new();
    let mut buf = Vec::new();
    let metric_families = REGISTRY.gather();
    encoder.encode(&metric_families, &mut buf)?;
    Ok(buf)
}

/// Force-initialise all default metrics (so they appear in `/metrics`
/// output before any traffic).
pub fn init() {
    Lazy::force(&INVOCATIONS);
    Lazy::force(&ERRORS);
    Lazy::force(&DURATION);
}

#[cfg(feature = "server")]
mod http {
    use super::*;
    use axum::{
        http::{header, HeaderValue, StatusCode},
        response::IntoResponse,
        routing::get,
        Router,
    };

    /// Axum router exposing `/metrics`.
    pub fn router() -> Router {
        Router::new().route(
            "/metrics",
            get(|| async {
                match render() {
                    Ok(buf) => (
                        StatusCode::OK,
                        [(
                            header::CONTENT_TYPE,
                            HeaderValue::from_static("text/plain; version=0.0.4"),
                        )],
                        buf,
                    )
                        .into_response(),
                    Err(e) => (
                        StatusCode::INTERNAL_SERVER_ERROR,
                        format!("encode error: {e}"),
                    )
                        .into_response(),
                }
            }),
        )
    }

    /// Bind the metrics HTTP server to `bind_addr`. Returns once the
    /// listener is up; spawns the serve task on the current tokio
    /// runtime and returns its `JoinHandle`.
    pub async fn serve(bind_addr: std::net::SocketAddr) -> Result<(), crate::Error> {
        init();
        let listener = tokio::net::TcpListener::bind(bind_addr)
            .await
            .map_err(crate::Error::Io)?;
        tracing::info!(%bind_addr, "metrics server listening");
        let app = router();
        axum::serve(listener, app)
            .await
            .map_err(|e| crate::Error::Server(Box::new(e)))?;
        Ok(())
    }
}

#[cfg(feature = "server")]
pub use http::{router, serve};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_includes_default_metrics() {
        init();
        inc_invocation();
        inc_error();
        observe_duration(std::time::Duration::from_millis(10));
        let body = render().expect("render");
        let s = String::from_utf8(body).expect("utf-8");
        assert!(s.contains("cli_invocations_total"));
        assert!(s.contains("cli_errors_total"));
        assert!(s.contains("cli_duration_seconds"));
    }

    #[test]
    fn render_does_not_panic_when_called_twice() {
        init();
        let _ = render().unwrap();
        let _ = render().unwrap();
    }
}
