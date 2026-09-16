//! HTTP `/health` endpoint for `phenotype-tooling-observability`.
//!
//! Returns a JSON body with process uptime. Backed by an axum router
//! behind the `server` feature.

use std::sync::OnceLock;
use std::time::Instant;

static START: OnceLock<Instant> = OnceLock::new();

/// Record the process start time. Idempotent — only the first call wins.
/// Public so integration tests can call it before exercising the handler.
pub fn mark_start() {
    START.get_or_init(Instant::now);
}

/// Current process uptime in seconds, or `0.0` if [`mark_start`] was
/// never called.
pub fn uptime_seconds() -> f64 {
    START
        .get()
        .map(|s| s.elapsed().as_secs_f64())
        .unwrap_or(0.0)
}

/// JSON body returned by `/health`.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, PartialEq)]
pub struct HealthReport {
    pub status: &'static str,
    pub uptime_s: f64,
}

impl HealthReport {
    /// Build the canonical report (`status: "ok"`, uptime since
    /// process start).
    pub fn current() -> Self {
        mark_start();
        Self {
            status: "ok",
            uptime_s: uptime_seconds(),
        }
    }
}

#[cfg(feature = "server")]
mod http {
    use super::*;
    use axum::{routing::get, Json, Router};

    /// Axum router exposing `/health`.
    pub fn router() -> Router {
        Router::new().route("/health", get(|| async { Json(HealthReport::current()) }))
    }

    /// Bind the health server to `bind_addr`. Same shape as
    /// [`super::super::metrics::serve`].
    pub async fn serve(bind_addr: std::net::SocketAddr) -> Result<(), crate::Error> {
        mark_start();
        let listener = tokio::net::TcpListener::bind(bind_addr)
            .await
            .map_err(crate::Error::Io)?;
        tracing::info!(%bind_addr, "health server listening");
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
    fn health_report_status_is_ok() {
        let r = HealthReport::current();
        assert_eq!(r.status, "ok");
        assert!(r.uptime_s >= 0.0);
    }

    #[test]
    fn uptime_is_monotonic_within_process() {
        let a = uptime_seconds();
        std::thread::sleep(std::time::Duration::from_millis(5));
        let b = uptime_seconds();
        assert!(b >= a);
    }

    #[test]
    fn report_serializes_to_json() {
        let r = HealthReport::current();
        let json = serde_json::to_string(&r).unwrap();
        assert!(json.contains("\"status\":\"ok\""));
        assert!(json.contains("uptime_s"));
    }
}
