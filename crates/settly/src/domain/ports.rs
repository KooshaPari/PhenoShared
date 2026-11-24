//! Port definitions - interfaces for external dependencies.

use super::config::Config;
use super::errors::ConfigError;

/// Port for configuration loaders.
pub trait LoaderPort: Send + Sync {
    /// Load configuration.
    fn load(&self) -> Result<Config, ConfigError>;
}

/// Port for configuration watchers.
#[async_trait::async_trait]
pub trait WatcherPort: Send + Sync {
    /// Start watching for changes.
    async fn watch<F>(&self, callback: F) -> Result<(), ConfigError>
    where
        F: Fn(Config) + Send + Sync + 'static;
}
