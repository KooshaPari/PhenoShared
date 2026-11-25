//! Shared tracing bootstrap used by AgilePlus binaries.

use tracing_subscriber::prelude::*;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::EnvFilter;

/// Initialize the process-wide tracing subscriber.
///
/// Uses `EnvFilter` so `RUST_LOG` can override behavior. When an OTLP endpoint
/// is configured, also attaches the crate-level telemetry layer.
pub fn init_tracing(service_name: &str, fallback_level: tracing::level_filters::LevelFilter) {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new(format!("{service_name}={fallback_level}")));

    let otlp_endpoint = std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
        .ok()
        .or_else(|| std::env::var("AGILEPLUS_OTLP_ENDPOINT").ok());

    let subscriber = tracing_subscriber::registry().with(env_filter).with(
        tracing_subscriber::fmt::layer()
            .with_target(false)
            .compact(),
    );

    if let Some(endpoint) = otlp_endpoint {
        std::env::set_var("OTEL_EXPORTER_OTLP_ENDPOINT", endpoint);

        if let Err(err) = crate::traces::init_tracer() {
            tracing::warn!(error = %err, "failed to initialize tracer provider");
            let _ = subscriber.try_init();
            return;
        }

        let subscriber = subscriber.with(crate::traces::telemetry_layer());
        let _ = subscriber.try_init();
        return;
    }

    let _ = subscriber.try_init();
}
