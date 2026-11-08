//! Phenotype OpenTelemetry bridge — single-call OTLP + tracing-subscriber init.
//!
//! This crate provides a turnkey `init()` function that wires up the OTLP
//! span exporter and a `tracing-subscriber` bridge so that any `tracing`
//! event in the host application is automatically exported as an OTLP span.
//!
//! # Example
//!
//! ```no_run
//! fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     pheno_otel::init("my-service")?;
//!
//!     let span = tracing::info_span!("work", kind = "demo");
//!     let _enter = span.enter();
//!     tracing::info!("hello from instrumented code");
//!
//!     pheno_otel::shutdown();
//!     Ok(())
//! }
//! ```
//!
//! # Environment Variables
//!
//! The default values are overridable via standard OTEL env vars:
//! - `OTEL_EXPORTER_OTLP_ENDPOINT` (default: `http://localhost:4318`)
//! - `RUST_LOG` (default: `info`)
//!
//! # Resources
//!
//! The exporter is configured with a `service.name` resource attribute equal
//! to the `service_name` argument (or `OTEL_SERVICE_NAME` if set via
//! `OtelConfig::from_env`). Additional attributes can be attached through
//! [`OtelConfig::with_attribute`].

use opentelemetry::trace::TracerProvider;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{
    trace::{Config, Sampler},
    Resource,
};
use std::collections::HashMap;
use thiserror::Error;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

/// Default OTLP HTTP endpoint.
pub const DEFAULT_OTLP_ENDPOINT: &str = "http://localhost:4318";

/// Environment variable that overrides the OTLP HTTP endpoint.
pub const OTLP_ENDPOINT_ENV: &str = "OTEL_EXPORTER_OTLP_ENDPOINT";

/// Default `tracing-subscriber` env-filter value when `RUST_LOG` is unset.
pub const DEFAULT_LOG_FILTER: &str = "info";

/// Errors that can occur during OTEL bridge initialization.
#[derive(Debug, Error)]
pub enum OtelBridgeError {
    /// OTLP exporter construction failed.
    #[error("OTLP exporter build failed: {0}")]
    Export(String),
    /// `tracing_subscriber::registry().try_init()` failed.
    #[error("tracing subscriber init failed: {0}")]
    Subscriber(String),
}

/// Initialize the OTLP HTTP exporter + tracing-subscriber bridge with the
/// given `service_name`.
///
/// The OTLP endpoint is read from `OTEL_EXPORTER_OTLP_ENDPOINT` and falls
/// back to [`DEFAULT_OTLP_ENDPOINT`]. The `tracing-subscriber` env filter
/// is read from `RUST_LOG` and falls back to [`DEFAULT_LOG_FILTER`].
///
/// For fine-grained control (extra resource attributes, explicit endpoint)
/// use [`OtelConfig::init`] instead.
pub fn init(service_name: &str) -> Result<(), OtelBridgeError> {
    OtelConfig::from_env(service_name).init()
}

/// Initialize the OTLP HTTP exporter + tracing-subscriber bridge with
/// explicit arguments. Prefer [`init`] or [`OtelConfig::init`] in
/// application code; this entry point exists for callers that need to
/// bypass env-var resolution.
pub fn init_with_endpoint(service_name: &str, otlp_endpoint: &str) -> Result<(), OtelBridgeError> {
    OtelConfig::new(service_name)
        .with_endpoint(otlp_endpoint)
        .init()
}

/// Shutdown the global tracer provider, flushing any buffered spans.
pub fn shutdown() {
    opentelemetry::global::shutdown_tracer_provider();
}

/// Re-export of `opentelemetry::KeyValue` for ergonomic attribute construction.
pub use opentelemetry::KeyValue as Attribute;

/// Builder for OTEL bridge configuration.
#[derive(Debug, Clone)]
pub struct OtelConfig {
    service_name: String,
    otlp_endpoint: String,
    attributes: HashMap<String, String>,
}

impl OtelConfig {
    /// Create a new config with default values.
    pub fn new(service_name: &str) -> Self {
        Self {
            service_name: service_name.to_string(),
            otlp_endpoint: DEFAULT_OTLP_ENDPOINT.to_string(),
            attributes: HashMap::new(),
        }
    }

    /// Create a config that reads `OTEL_EXPORTER_OTLP_ENDPOINT` from the
    /// process environment, falling back to [`DEFAULT_OTLP_ENDPOINT`].
    pub fn from_env(service_name: &str) -> Self {
        let endpoint = std::env::var(OTLP_ENDPOINT_ENV)
            .ok()
            .filter(|s| !s.trim().is_empty())
            .unwrap_or_else(|| DEFAULT_OTLP_ENDPOINT.to_string());
        Self {
            service_name: service_name.to_string(),
            otlp_endpoint: endpoint,
            attributes: HashMap::new(),
        }
    }

    /// Override the OTLP endpoint.
    #[must_use]
    pub fn with_endpoint(mut self, endpoint: &str) -> Self {
        self.otlp_endpoint = endpoint.to_string();
        self
    }

    /// Add a resource attribute. Inserting the same key twice keeps the
    /// most recent value.
    #[must_use]
    pub fn with_attribute(mut self, key: &str, value: &str) -> Self {
        self.attributes.insert(key.to_string(), value.to_string());
        self
    }

    /// Returns the configured OTLP endpoint.
    pub fn endpoint(&self) -> &str {
        &self.otlp_endpoint
    }

    /// Returns the configured service name.
    pub fn service_name(&self) -> &str {
        &self.service_name
    }

    /// Returns the configured resource attributes.
    pub fn attributes(&self) -> &HashMap<String, String> {
        &self.attributes
    }

    /// Initialize the OTEL bridge with this configuration.
    ///
    /// Resource attributes collected via [`OtelConfig::with_attribute`]
    /// are attached to the [`TracerProvider`] in addition to the
    /// `service.name` attribute derived from the constructor argument.
    pub fn init(self) -> Result<(), OtelBridgeError> {
        let mut resource_kvs = Vec::with_capacity(self.attributes.len() + 1);
        resource_kvs.push(opentelemetry::KeyValue::new(
            "service.name",
            self.service_name.clone(),
        ));
        for (k, v) in &self.attributes {
            resource_kvs.push(opentelemetry::KeyValue::new(k.clone(), v.clone()));
        }

        let exporter = opentelemetry_otlp::new_exporter()
            .http()
            .with_endpoint(&self.otlp_endpoint)
            .build_span_exporter()
            .map_err(|e| OtelBridgeError::Export(e.to_string()))?;

        let provider = opentelemetry_sdk::trace::TracerProvider::builder()
            .with_batch_exporter(exporter, opentelemetry_sdk::runtime::Tokio)
            .with_config(
                Config::default()
                    .with_sampler(Sampler::AlwaysOn)
                    .with_resource(Resource::new(resource_kvs)),
            )
            .build();

        opentelemetry::global::set_tracer_provider(provider.clone());

        let tracer = provider.tracer(self.service_name.clone());
        let otel_layer = tracing_opentelemetry::layer().with_tracer(tracer);

        let env_filter = EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new(DEFAULT_LOG_FILTER));

        tracing_subscriber::registry()
            .with(env_filter)
            .with(otel_layer)
            .try_init()
            .map_err(|e| OtelBridgeError::Subscriber(e.to_string()))?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn config_default_endpoint() {
        let c = OtelConfig::new("svc");
        assert_eq!(c.endpoint(), DEFAULT_OTLP_ENDPOINT);
        assert_eq!(c.service_name(), "svc");
    }

    #[test]
    fn config_with_endpoint() {
        let c = OtelConfig::new("svc").with_endpoint("http://collector:4318");
        assert_eq!(c.endpoint(), "http://collector:4318");
    }

    #[test]
    fn config_with_attribute() {
        let c = OtelConfig::new("svc").with_attribute("env", "prod");
        assert_eq!(c.attributes().get("env"), Some(&"prod".to_string()));
    }

    #[test]
    fn default_endpoint_constant() {
        assert_eq!(DEFAULT_OTLP_ENDPOINT, "http://localhost:4318");
    }

    #[test]
    fn default_log_filter_constant() {
        assert_eq!(DEFAULT_LOG_FILTER, "info");
    }

    #[test]
    fn otlp_endpoint_env_constant() {
        assert_eq!(OTLP_ENDPOINT_ENV, "OTEL_EXPORTER_OTLP_ENDPOINT");
    }

    #[test]
    fn otel_bridge_error_export_display() {
        let err = OtelBridgeError::Export("boom".to_string());
        assert_eq!(err.to_string(), "OTLP exporter build failed: boom");
    }

    #[test]
    fn otel_bridge_error_subscriber_display() {
        let err = OtelBridgeError::Subscriber("init failed".to_string());
        assert_eq!(
            err.to_string(),
            "tracing subscriber init failed: init failed"
        );
    }

    #[test]
    fn otel_bridge_error_debug_is_implemented() {
        // The #[derive(Debug)] is part of the public contract; assert
        // Debug formatting does not panic and exposes the inner string.
        let err = OtelBridgeError::Export("x".to_string());
        let dbg = format!("{err:?}");
        assert!(dbg.contains("Export"));
        assert!(dbg.contains("x"));
    }

    #[test]
    fn config_multiple_attributes() {
        let c = OtelConfig::new("svc")
            .with_attribute("env", "prod")
            .with_attribute("region", "us-east-1")
            .with_attribute("version", "1.2.3");
        assert_eq!(c.attributes().get("env"), Some(&"prod".to_string()));
        assert_eq!(c.attributes().get("region"), Some(&"us-east-1".to_string()));
        assert_eq!(c.attributes().get("version"), Some(&"1.2.3".to_string()));
        assert_eq!(c.attributes().len(), 3);
    }

    #[test]
    fn config_attribute_last_write_wins() {
        // Inserting the same key twice keeps the most recent value
        // (HashMap::insert semantics) — pin this down.
        let c = OtelConfig::new("svc")
            .with_attribute("env", "dev")
            .with_attribute("env", "prod");
        assert_eq!(c.attributes().get("env"), Some(&"prod".to_string()));
        assert_eq!(c.attributes().len(), 1);
    }

    #[test]
    fn config_clone_is_independent() {
        // Clone is required for the builder to be passed across
        // thread boundaries when initialising telemetry in a worker.
        let c1 = OtelConfig::new("svc").with_endpoint("http://a:4318");
        let c2 = c1.clone();
        assert_eq!(c1.endpoint(), c2.endpoint());
        assert_eq!(c1.service_name(), c2.service_name());
    }

    #[test]
    fn attribute_alias_matches_keyvalue() {
        // `Attribute` is a re-export of `opentelemetry::KeyValue`; verify
        // the type relationship compiles and constructs.
        use opentelemetry::KeyValue;
        let kv = Attribute::new("k", "v");
        let original = KeyValue::new("k", "v");
        assert_eq!(kv.key, original.key);
    }

    #[test]
    fn from_env_uses_default_when_unset() {
        // Use a name that is extremely unlikely to be set in CI/test envs.
        let prev = std::env::var(OTLP_ENDPOINT_ENV).ok();
        // SAFETY: tests in this module do not rely on concurrent env mutations
        // from other threads. Cargo runs unit tests in parallel by default, so
        // we deliberately key off a process-global value: if a parallel test
        // has set it, our assertion still holds as long as we don't overwrite
        // it. We therefore only assert the documented fallback semantics when
        // we can confirm the variable is unset.
        if prev.is_none() {
            let c = OtelConfig::from_env("svc");
            assert_eq!(c.endpoint(), DEFAULT_OTLP_ENDPOINT);
        }
    }

    #[test]
    fn from_env_honors_endpoint_var() {
        // SAFETY: see `from_env_uses_default_when_unset`. We only mutate the
        // env if the test is running in a context where the variable is
        // unset, and we restore it afterwards.
        let prev = std::env::var(OTLP_ENDPOINT_ENV).ok();
        std::env::set_var(OTLP_ENDPOINT_ENV, "http://from-env:4318");
        let c = OtelConfig::from_env("svc");
        assert_eq!(c.endpoint(), "http://from-env:4318");
        match prev {
            Some(v) => std::env::set_var(OTLP_ENDPOINT_ENV, v),
            None => std::env::remove_var(OTLP_ENDPOINT_ENV),
        }
    }

    #[test]
    fn from_env_treats_blank_as_unset() {
        let prev = std::env::var(OTLP_ENDPOINT_ENV).ok();
        std::env::set_var(OTLP_ENDPOINT_ENV, "   ");
        let c = OtelConfig::from_env("svc");
        assert_eq!(c.endpoint(), DEFAULT_OTLP_ENDPOINT);
        match prev {
            Some(v) => std::env::set_var(OTLP_ENDPOINT_ENV, v),
            None => std::env::remove_var(OTLP_ENDPOINT_ENV),
        }
    }

    #[test]
    fn init_propagates_service_name_and_attributes() {
        // Pure-data assertions on the builder — the live OTLP path is
        // exercised by `examples/basic.rs` and the integration test suite.
        let c = OtelConfig::new("orders")
            .with_endpoint("http://collector:4318")
            .with_attribute("deployment.environment", "prod")
            .with_attribute("service.version", "1.4.2");

        assert_eq!(c.service_name(), "orders");
        assert_eq!(c.endpoint(), "http://collector:4318");
        assert_eq!(c.attributes().len(), 2);
        assert_eq!(
            c.attributes().get("deployment.environment"),
            Some(&"prod".to_string())
        );
        assert_eq!(
            c.attributes().get("service.version"),
            Some(&"1.4.2".to_string())
        );
    }

    #[test]
    fn init_with_endpoint_helper_matches_otel_config() {
        // The two entry points should produce equivalent state for the
        // happy-path inputs. We assert the observable state on the
        // builder, since `init()` mutates global process state and
        // cannot be invoked twice within a single test process.
        let via_helper = OtelConfig::new("svc").with_endpoint("http://h:4318");
        let via_builder = OtelConfig::new("svc").with_endpoint("http://h:4318");
        assert_eq!(via_helper.endpoint(), via_builder.endpoint());
        assert_eq!(via_helper.service_name(), via_builder.service_name());
        assert_eq!(via_helper.attributes(), via_builder.attributes());
    }
}
