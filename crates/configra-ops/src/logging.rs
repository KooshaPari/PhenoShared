//! Structured logging via `tracing` with level and format controls.

use std::io;

use tracing_subscriber::filter::LevelFilter;
use tracing_subscriber::fmt::format::FmtSpan;
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::util::SubscriberInitExt;
use tracing_subscriber::EnvFilter;

/// Log output format.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum LogFormat {
    /// Human-readable lines (development).
    #[default]
    Pretty,
    /// JSON lines (production / log aggregators).
    Json,
}

impl LogFormat {
    /// Parse from `CONFIGRA_LOG_FORMAT` (`pretty` | `json`).
    pub fn from_env() -> Self {
        match std::env::var("CONFIGRA_LOG_FORMAT")
            .unwrap_or_else(|_| "pretty".into())
            .to_ascii_lowercase()
            .as_str()
        {
            "json" => Self::Json,
            _ => Self::Pretty,
        }
    }
}

/// Logging bootstrap configuration.
#[derive(Debug, Clone)]
pub struct LoggingConfig {
    /// Filter directive (e.g. `info`, `configra_ops=debug`).
    pub level: String,
    /// Output format.
    pub format: LogFormat,
    /// Emit span close events (useful for latency tracing).
    pub log_spans: bool,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            level: std::env::var("CONFIGRA_LOG_LEVEL")
                .or_else(|_| std::env::var("RUST_LOG"))
                .unwrap_or_else(|_| "info".into()),
            format: LogFormat::from_env(),
            log_spans: true,
        }
    }
}

/// Initialize global `tracing` subscriber. Safe to call once per process.
///
/// Returns the resolved level filter on success.
pub fn init_logging(config: &LoggingConfig) -> anyhow::Result<tracing::Level> {
    let filter = EnvFilter::try_new(&config.level)?;
    let level = match filter.max_level_hint().unwrap_or(LevelFilter::INFO) {
        LevelFilter::TRACE => tracing::Level::TRACE,
        LevelFilter::DEBUG => tracing::Level::DEBUG,
        LevelFilter::INFO => tracing::Level::INFO,
        LevelFilter::WARN => tracing::Level::WARN,
        LevelFilter::ERROR => tracing::Level::ERROR,
        LevelFilter::OFF => tracing::Level::ERROR, // fallback for OFF
    };

    let span_events = if config.log_spans {
        FmtSpan::CLOSE
    } else {
        FmtSpan::NONE
    };

    let registry = tracing_subscriber::registry().with(filter);

    match config.format {
        LogFormat::Pretty => {
            registry
                .with(
                    tracing_subscriber::fmt::layer()
                        .with_writer(io::stderr)
                        .with_span_events(span_events)
                        .with_target(true)
                        .with_thread_ids(true)
                        .with_level(true),
                )
                .try_init()
                .map_err(|e| anyhow::anyhow!("tracing already initialized: {e}"))?;
        },
        LogFormat::Json => {
            registry
                .with(
                    tracing_subscriber::fmt::layer()
                        .json()
                        .with_writer(io::stderr)
                        .with_span_events(span_events)
                        .with_current_span(true)
                        .with_span_list(true),
                )
                .try_init()
                .map_err(|e| anyhow::anyhow!("tracing already initialized: {e}"))?;
        },
    }

    tracing::info!(
        target: "configra_ops",
        level = %level,
        format = ?config.format,
        "structured logging initialized"
    );
    Ok(level)
}
