//! OTLP metrics export (C05 L43 / L42).
//!
//! Default builds keep dependency-free Prometheus text at `GET /metrics`.
//! Enable `--features otel-metrics` and set `SL_OTLP_METRICS_ENDPOINT` or
//! `OTEL_EXPORTER_OTLP_ENDPOINT` to push metrics over OTLP/gRPC. Prometheus
//! `/metrics` remains the default scrape path.

/// Legacy operator acknowledgment env (no endpoint required).
pub const ENV_OTLP_METRICS: &str = "SL_OTLP_METRICS";

/// SessionLedger OTLP metrics collector endpoint (gRPC).
pub const ENV_OTLP_METRICS_ENDPOINT: &str = "SL_OTLP_METRICS_ENDPOINT";

/// OpenTelemetry-standard fallback when the SessionLedger variable is unset.
pub const ENV_OTEL_EXPORTER_OTLP_ENDPOINT: &str = "OTEL_EXPORTER_OTLP_ENDPOINT";

/// Resolve the OTLP metrics collector endpoint, if configured.
#[must_use]
pub fn metrics_endpoint() -> Option<String> {
    std::env::var(ENV_OTLP_METRICS_ENDPOINT).ok().filter(|value| !value.trim().is_empty()).or_else(
        || {
            std::env::var(ENV_OTEL_EXPORTER_OTLP_ENDPOINT)
                .ok()
                .filter(|value| !value.trim().is_empty())
        },
    )
}

/// Returns whether the soft OTLP metrics stub is operator-acknowledged.
#[must_use]
pub fn stub_acknowledged() -> bool {
    std::env::var(ENV_OTLP_METRICS).is_ok_and(|value| {
        let trimmed = value.trim();
        trimmed == "1"
            || trimmed.eq_ignore_ascii_case("true")
            || trimmed.eq_ignore_ascii_case("yes")
    })
}

/// Initialize OTLP metrics export when an endpoint is configured.
///
/// Returns the meter provider so the caller can flush during graceful shutdown.
/// When no endpoint is set but `SL_OTLP_METRICS=1`, logs acknowledgment only.
#[cfg(feature = "otel-metrics")]
pub fn maybe_init() -> Option<opentelemetry_sdk::metrics::SdkMeterProvider> {
    if let Some(endpoint) = metrics_endpoint() {
        match init_exporter(&endpoint) {
            Ok(provider) => return Some(provider),
            Err(error) => {
                eprintln!(
                    "warning: failed to initialize OTLP metrics export for {endpoint:?}: {error}; \
                     continuing with Prometheus /metrics only"
                );
            }
        }
    }

    maybe_log_stub_status();
    None
}

#[cfg(feature = "otel-metrics")]
fn init_exporter(
    endpoint: &str,
) -> Result<opentelemetry_sdk::metrics::SdkMeterProvider, Box<dyn std::error::Error>> {
    use opentelemetry::global;
    use opentelemetry::metrics::MeterProvider as _;
    use opentelemetry_otlp::WithExportConfig as _;
    use opentelemetry_sdk::metrics::SdkMeterProvider;

    let exporter = opentelemetry_otlp::MetricExporter::builder()
        .with_tonic()
        .with_endpoint(endpoint)
        .build()?;

    let provider = SdkMeterProvider::builder().with_periodic_exporter(exporter).build();

    global::set_meter_provider(provider.clone());

    let meter = provider.meter("sl-daemon");
    let gauge = meter
        .f64_gauge("sl_daemon_otlp_metrics_up")
        .with_description("OTLP metrics export enabled for sl-daemon")
        .build();
    gauge.record(1.0, &[]);

    tracing::info!(
        target: "sl_daemon::otel_metrics",
        metrics_export = "otlp-grpc",
        endpoint = %endpoint,
        prometheus_http = "/metrics",
        "OTLP metrics export initialized; Prometheus /metrics unchanged"
    );

    Ok(provider)
}

/// Emit a one-shot info line when the stub is acknowledged without an endpoint.
///
/// Does not alter Prometheus `/metrics` output.
pub fn maybe_log_stub_status() {
    if stub_acknowledged() && metrics_endpoint().is_none() {
        tracing::info!(
            target: "sl_daemon::otel_metrics",
            metrics_export = "stub",
            prometheus_http = "/metrics",
            "OTLP metrics export stub acknowledged (SL_OTLP_METRICS); \
             set SL_OTLP_METRICS_ENDPOINT to enable OTLP/gRPC push — Prometheus /metrics unchanged"
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn env_constants_match_ops_ssot() {
        assert_eq!(ENV_OTLP_METRICS, "SL_OTLP_METRICS");
        assert_eq!(ENV_OTLP_METRICS_ENDPOINT, "SL_OTLP_METRICS_ENDPOINT");
        assert_eq!(ENV_OTEL_EXPORTER_OTLP_ENDPOINT, "OTEL_EXPORTER_OTLP_ENDPOINT");
    }

    #[test]
    fn stub_acknowledged_parses_truthy_values() {
        std::env::remove_var(ENV_OTLP_METRICS);
        assert!(!stub_acknowledged());

        std::env::set_var(ENV_OTLP_METRICS, "1");
        assert!(stub_acknowledged());

        std::env::set_var(ENV_OTLP_METRICS, "true");
        assert!(stub_acknowledged());

        std::env::set_var(ENV_OTLP_METRICS, "0");
        assert!(!stub_acknowledged());

        std::env::remove_var(ENV_OTLP_METRICS);
    }

    #[test]
    fn metrics_endpoint_prefers_sessionledger_env() {
        std::env::remove_var(ENV_OTLP_METRICS_ENDPOINT);
        std::env::remove_var(ENV_OTEL_EXPORTER_OTLP_ENDPOINT);
        assert!(metrics_endpoint().is_none());

        std::env::set_var(ENV_OTEL_EXPORTER_OTLP_ENDPOINT, "http://otel-fallback:4317");
        assert_eq!(metrics_endpoint().as_deref(), Some("http://otel-fallback:4317"));

        std::env::set_var(ENV_OTLP_METRICS_ENDPOINT, "http://sl-metrics:4317");
        assert_eq!(metrics_endpoint().as_deref(), Some("http://sl-metrics:4317"));

        std::env::remove_var(ENV_OTLP_METRICS_ENDPOINT);
        std::env::remove_var(ENV_OTEL_EXPORTER_OTLP_ENDPOINT);
    }

    #[test]
    fn metrics_endpoint_ignores_blank_values() {
        std::env::set_var(ENV_OTLP_METRICS_ENDPOINT, "   ");
        std::env::remove_var(ENV_OTEL_EXPORTER_OTLP_ENDPOINT);
        assert!(metrics_endpoint().is_none());
        std::env::remove_var(ENV_OTLP_METRICS_ENDPOINT);
    }
}
