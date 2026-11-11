//! Feature-gated OTLP trace export.

use std::{collections::HashMap, env, error::Error};

use opentelemetry::trace::TracerProvider as _;
use opentelemetry_otlp::WithExportConfig as _;
use opentelemetry_sdk::trace::SdkTracerProvider;
use tracing_subscriber::{layer::SubscriberExt as _, util::SubscriberInitExt as _, EnvFilter};

pub const ENV_LANGFUSE_ENABLED: &str = "SL_LANGFUSE_ENABLED";
pub const ENV_LANGFUSE_ENDPOINT: &str = "SL_LANGFUSE_OTLP_ENDPOINT";
pub const ENV_LANGFUSE_PUBLIC_KEY: &str = "SL_LANGFUSE_PUBLIC_KEY";
pub const ENV_LANGFUSE_SECRET_KEY: &str = "SL_LANGFUSE_SECRET_KEY";

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct LangfuseConfig {
    pub endpoint: String,
    pub authorization: String,
}

impl LangfuseConfig {
    pub(crate) fn from_env() -> Result<Option<Self>, Box<dyn Error>> {
        let enabled =
            env::var(ENV_LANGFUSE_ENABLED).is_ok_and(|v| matches!(v.trim(), "1" | "true" | "yes"));
        Self::from_values(
            enabled,
            env::var(ENV_LANGFUSE_ENDPOINT).ok(),
            env::var(ENV_LANGFUSE_PUBLIC_KEY).ok(),
            env::var(ENV_LANGFUSE_SECRET_KEY).ok(),
        )
    }

    fn from_values(
        enabled: bool,
        endpoint: Option<String>,
        public: Option<String>,
        secret: Option<String>,
    ) -> Result<Option<Self>, Box<dyn Error>> {
        if !enabled {
            return Ok(None);
        }
        let endpoint = endpoint
            .ok_or("SL_LANGFUSE_OTLP_ENDPOINT is required when Langfuse export is enabled")?;
        let public =
            public.ok_or("SL_LANGFUSE_PUBLIC_KEY is required when Langfuse export is enabled")?;
        let secret =
            secret.ok_or("SL_LANGFUSE_SECRET_KEY is required when Langfuse export is enabled")?;
        if endpoint.trim().is_empty() || public.trim().is_empty() || secret.trim().is_empty() {
            return Err("Langfuse endpoint and keys must not be blank".into());
        }
        let authorization = base64::Engine::encode(
            &base64::engine::general_purpose::STANDARD,
            format!("{public}:{secret}"),
        );
        Ok(Some(Self {
            endpoint: endpoint.trim_end_matches('/').to_owned(),
            authorization: format!("Basic {authorization}"),
        }))
    }
}

/// Install the normal formatting layer plus an OTLP tracing layer.
///
/// The provider is returned so the caller can keep it alive and flush it
/// during a graceful shutdown.
pub(crate) fn init(
    filter: EnvFilter,
    endpoint: &str,
    json_logs: bool,
) -> Result<SdkTracerProvider, Box<dyn Error>> {
    let exporter =
        opentelemetry_otlp::SpanExporter::builder().with_tonic().with_endpoint(endpoint).build()?;
    let provider = SdkTracerProvider::builder().with_batch_exporter(exporter).build();
    let tracer = provider.tracer("sl-daemon");

    #[cfg(feature = "json-logs")]
    if json_logs {
        tracing_subscriber::registry()
            .with(filter)
            .with(tracing_subscriber::fmt::layer().json().with_target(true))
            .with(tracing_opentelemetry::layer().with_tracer(tracer))
            .try_init()?;
        return Ok(provider);
    }

    let _ = json_logs;
    tracing_subscriber::registry()
        .with(filter)
        .with(tracing_subscriber::fmt::layer().with_target(true))
        .with(tracing_opentelemetry::layer().with_tracer(tracer))
        .try_init()?;

    Ok(provider)
}

pub(crate) fn init_langfuse(
    filter: EnvFilter,
    config: &LangfuseConfig,
    json_logs: bool,
) -> Result<SdkTracerProvider, Box<dyn Error>> {
    use opentelemetry_otlp::WithHttpConfig;
    let mut headers = HashMap::new();
    headers.insert("Authorization".to_owned(), config.authorization.clone());
    let exporter = opentelemetry_otlp::SpanExporter::builder()
        .with_http()
        .with_endpoint(config.endpoint.clone())
        .with_headers(headers)
        .build()?;
    let provider = SdkTracerProvider::builder().with_batch_exporter(exporter).build();
    let tracer = provider.tracer("sl-daemon");
    let fmt = tracing_subscriber::fmt::layer().with_target(true);
    #[cfg(feature = "json-logs")]
    if json_logs {
        tracing_subscriber::registry()
            .with(filter)
            .with(fmt.json())
            .with(tracing_opentelemetry::layer().with_tracer(tracer))
            .try_init()?;
        return Ok(provider);
    }
    let _ = json_logs;
    tracing_subscriber::registry()
        .with(filter)
        .with(fmt)
        .with(tracing_opentelemetry::layer().with_tracer(tracer))
        .try_init()?;
    Ok(provider)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_by_default() {
        assert_eq!(LangfuseConfig::from_values(false, None, None, None).unwrap(), None);
    }

    #[test]
    fn config_normalizes_endpoint_and_builds_basic_auth() {
        let config = LangfuseConfig::from_values(
            true,
            Some("https://example.test/v1/traces///".into()),
            Some("public".into()),
            Some("secret".into()),
        )
        .unwrap()
        .unwrap();
        assert_eq!(config.endpoint, "https://example.test/v1/traces");
        assert_eq!(config.authorization, "Basic cHVibGljOnNlY3JldA==");
    }

    #[test]
    fn enabled_config_requires_all_credentials() {
        let error =
            LangfuseConfig::from_values(true, Some("https://example.test".into()), None, None)
                .unwrap_err()
                .to_string();
        assert!(error.contains(ENV_LANGFUSE_PUBLIC_KEY));
    }
}
