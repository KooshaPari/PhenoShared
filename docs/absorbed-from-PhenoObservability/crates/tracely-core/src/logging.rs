//! Structured logging helpers with correlation IDs and JSON output.
//!
//! Absorbed from `helix-logging` (archived 2026-03-26).
//! Original: <https://github.com/KooshaPari/helix-logging>

pub use log::{debug, error, info, trace, warn, Level, LevelFilter, Metadata, Record};

/// Configuration for the logger.
#[derive(Debug, Clone)]
pub struct LoggerConfig {
    /// Minimum log level to capture.
    pub level: Level,
    /// Include timestamps in log output.
    pub include_timestamps: bool,
    /// Include file and line information in log output.
    pub include_location: bool,
    /// Correlation ID for tracing requests across service boundaries.
    pub correlation_id: Option<String>,
}

impl Default for LoggerConfig {
    fn default() -> Self {
        Self {
            level: Level::Info,
            include_timestamps: true,
            include_location: true,
            correlation_id: None,
        }
    }
}

/// Initialize the logger with the given configuration.
///
/// Safe to call multiple times; subsequent calls are silently ignored.
pub fn init(config: LoggerConfig) {
    env_logger::Builder::new()
        .filter_level(config.level.to_level_filter())
        .format(|buf, record| {
            use std::io::Write;
            write!(
                buf,
                "[{}] {} - {}",
                record.level(),
                chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.3f"),
                record.args()
            )
        })
        .try_init()
        .ok();
}

/// Emit a JSON-formatted log at the given level.
///
/// # Example
///
/// ```rust
/// use tracely_core::log_json;
/// use log::Level;
///
/// log_json!(Level::Info, "event" = "request", "status" = 200u16);
/// ```
#[macro_export]
macro_rules! log_json {
    ($level:expr, $($key:tt = $value:expr),+ $(,)?) => {
        {
            use serde_json::json;
            let obj = json!({ $($key: $value),+ });
            log::log!($level, "{}", obj);
        }
    };
}

/// Wraps a correlation ID for propagating request context across service calls.
pub struct LogContext {
    /// The correlation ID, either caller-supplied or auto-generated as a UUID v4.
    pub correlation_id: String,
}

impl LogContext {
    /// Create a new context. If `id` is `None`, a UUID v4 is generated.
    pub fn new(id: Option<String>) -> Self {
        Self {
            correlation_id: id.unwrap_or_else(|| uuid::Uuid::new_v4().to_string()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_logger_config_default() {
        let config = LoggerConfig::default();
        assert_eq!(config.level, Level::Info);
        assert!(config.include_timestamps);
        assert!(config.include_location);
        assert!(config.correlation_id.is_none());
    }

    #[test]
    fn test_log_context_auto_generation() {
        let ctx = LogContext::new(None);
        assert!(!ctx.correlation_id.is_empty());
    }

    #[test]
    fn test_log_context_with_provided_id() {
        let ctx = LogContext::new(Some("test-123".to_string()));
        assert_eq!(ctx.correlation_id, "test-123");
    }

    #[test]
    fn test_log_context_ids_are_unique() {
        let a = LogContext::new(None);
        let b = LogContext::new(None);
        assert_ne!(a.correlation_id, b.correlation_id);
    }
}
