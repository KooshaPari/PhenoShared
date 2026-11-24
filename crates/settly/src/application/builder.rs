//! Configuration builder.

use std::collections::HashMap;

use crate::domain::{
    sources::Source, validation::Validator, Config, ConfigError, ConfigValue, LayerPriority,
    LayerStack, MergeStrategy,
};

/// Builder for constructing configurations.
pub struct ConfigBuilder {
    stack: LayerStack,
    validators: Vec<Box<dyn Validator>>,
}

impl ConfigBuilder {
    /// Create a new builder.
    pub fn new() -> Self {
        Self { stack: LayerStack::new(), validators: Vec::new() }
    }

    /// Create with a merge strategy.
    pub fn with_strategy(strategy: MergeStrategy) -> Self {
        Self { stack: LayerStack::with_strategy(strategy), validators: Vec::new() }
    }

    /// Add a source with priority.
    pub async fn with_source<S: Source>(
        mut self,
        source: S,
        priority: LayerPriority,
    ) -> Result<Self, ConfigError> {
        let config = source.load().await?;
        self.stack.add(source.name(), priority, config);
        Ok(self)
    }

    /// Add a source from a config map.
    pub fn with_values(
        mut self,
        name: impl Into<String>,
        priority: LayerPriority,
        values: HashMap<String, serde_json::Value>,
    ) -> Self {
        let mut config = Config::new();
        for (key, value) in values {
            config.set(key, ConfigValue::from_json(&value));
        }
        self.stack.add(name, priority, config);
        self
    }

    /// Add environment variables as a layer.
    pub fn with_env(mut self) -> Self {
        let mut config = Config::new();
        for (key, value) in std::env::vars() {
            config.set(key, value);
        }
        self.stack.add("env", LayerPriority::EnvVars, config);
        self
    }

    /// Add CLI arguments as a layer.
    pub fn with_cli_args(self) -> Self {
        // In real implementation, parse CLI args
        self
    }

    /// Add a validator.
    pub fn with_validator<V: Validator + 'static>(mut self, validator: V) -> Self {
        self.validators.push(Box::new(validator));
        self
    }

    /// Add a default value layer.
    pub fn with_default(mut self, values: HashMap<String, serde_json::Value>) -> Self {
        let mut config = Config::new();
        for (key, value) in values {
            config.set(key, ConfigValue::from_json(&value));
        }
        self.stack.add("default", LayerPriority::Default, config);
        self
    }

    /// Build the final configuration.
    pub fn build(self) -> Result<Config, ConfigError> {
        let config = self.stack.merge();

        // Run validators
        for validator in &self.validators {
            validator.validate(&config)?;
        }

        Ok(config)
    }

    /// Build and validate synchronously.
    pub fn build_sync(self) -> Result<Config, ConfigError> {
        // For sources that don't need async
        self.build()
    }
}

impl Default for ConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}
