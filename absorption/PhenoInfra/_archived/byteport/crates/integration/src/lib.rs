use pheno_errors::AppError;
use pheno_tracing;
use serde::Deserialize;
use std::path::Path;

/// BytePort application configuration.
#[derive(Debug, Clone, Deserialize, PartialEq)]
pub struct BytePortConfig {
    pub name: String,
    pub port: Option<u16>,
}

/// Canonical BytePort application struct.
///
/// Wires `pheno-errors`, `pheno-tracing`, and `pheno-config` into a
/// single entry point.
#[derive(Debug, Clone)]
pub struct BytePortApp {
    pub config: BytePortConfig,
}

impl BytePortApp {
    /// Create a new `BytePortApp` by loading configuration from the
    /// environment with the given `prefix` and initializing tracing.
    ///
    /// # Errors
    ///
    /// Returns `AppError` if configuration loading fails.
    pub fn new(prefix: &str) -> Result<Self, AppError> {
        let config: BytePortConfig = pheno_config::load_from_env(prefix)
            .map_err(|e| AppError::domain(format!("config load failed: {e}")))?;
        Ok(Self { config })
    }

    /// Create a new `BytePortApp` with an explicit config value.
    ///
    /// Useful for testing and for callers that already have a config
    /// object.
    pub fn with_config(config: BytePortConfig) -> Self {
        Self { config }
    }

    /// Initialize the tracing subsystem.
    ///
    /// Idempotent (uses `try_init` internally).
    pub fn init_tracing(&self) {
        pheno_tracing::init();
    }

    /// Initialize the tracing subsystem with structured JSON output.
    pub fn init_tracing_json(&self) {
        pheno_tracing::init_json();
    }

    /// Initialize the tracing subsystem with a daily-rotated file appender.
    pub fn init_tracing_file(&self, dir: &Path) {
        pheno_tracing::init_with_file(dir);
    }

    /// Run the application.
    ///
    /// 1. Initializes tracing.
    /// 2. Logs a startup span.
    /// 3. Returns `Ok(())` on success.
    pub fn run(&self) -> Result<(), AppError> {
        self.init_tracing();
        tracing::info!(app.name = %self.config.name, "BytePortApp started");
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_loads_config() {
        std::env::set_var("BPTEST_NAME", "byteport-test");
        std::env::set_var("BPTEST_PORT", "8080");

        let app = BytePortApp::new("BPTEST_").expect("app should load config");
        assert_eq!(app.config.name, "byteport-test");
        assert_eq!(app.config.port, Some(8080));
    }

    #[test]
    fn app_initializes_tracing() {
        let app = BytePortApp::with_config(BytePortConfig {
            name: "byteport-tracing-test".into(),
            port: None,
        });
        app.init_tracing();
        // If tracing is already initialized by another test, this is a
        // no-op. The important thing is that the call does not panic.
        tracing::info!("tracing initialized successfully");
    }
}
