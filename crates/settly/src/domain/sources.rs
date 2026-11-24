//! Configuration source definitions.

use async_trait::async_trait;

use super::config::Config;
use super::errors::ConfigError;

/// Trait for configuration sources.
#[async_trait]
pub trait Source: Send + Sync {
    /// Source name (e.g., "file", "env", "cli").
    fn name(&self) -> &str;

    /// Load configuration from this source.
    async fn load(&self) -> Result<Config, ConfigError>;

    /// Check if this source is available.
    fn is_available(&self) -> bool {
        true
    }
}

/// Trait for sources that can be watched for changes.
#[async_trait]
pub trait WatchableSource: Source {
    /// Start watching for changes.
    async fn watch<F>(&self, callback: F) -> Result<(), ConfigError>
    where
        F: Fn(Config) + Send + Sync;
}

/// Null source - always returns empty config.
pub struct NullSource;

#[async_trait]
impl Source for NullSource {
    fn name(&self) -> &str {
        "null"
    }

    async fn load(&self) -> Result<Config, ConfigError> {
        Ok(Config::new())
    }
}
