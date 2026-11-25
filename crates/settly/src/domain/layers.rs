//! Configuration layer management.

use serde::{Deserialize, Serialize};

use super::config::Config;

/// Layer priority levels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize, Default)]
#[repr(u8)]
pub enum LayerPriority {
    /// Built-in defaults (lowest priority).
    #[default]
    Default = 10,
    /// Environment-specific files.
    Env = 30,
    /// User home directory configs.
    Home = 40,
    /// Project/local configs.
    Local = 50,
    /// Environment variables.
    EnvVars = 60,
    /// CLI arguments (highest priority).
    Cli = 100,
}

/// A configuration layer with priority.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Layer {
    /// Layer name.
    pub name: String,
    /// Priority (higher = more important).
    pub priority: LayerPriority,
    /// Configuration values.
    pub config: Config,
}

impl Layer {
    /// Create a new layer.
    pub fn new(name: impl Into<String>, priority: LayerPriority, config: Config) -> Self {
        Self { name: name.into(), priority, config }
    }

    /// Create a default layer.
    pub fn default_layer(config: Config) -> Self {
        Self::new("default", LayerPriority::Default, config)
    }

    /// Create an environment layer.
    pub fn env_layer(name: impl Into<String>, config: Config) -> Self {
        Self::new(name, LayerPriority::Env, config)
    }

    /// Create a local layer.
    pub fn local_layer(name: impl Into<String>, config: Config) -> Self {
        Self::new(name, LayerPriority::Local, config)
    }

    /// Create an env vars layer.
    pub fn env_vars_layer(config: Config) -> Self {
        Self::new("env", LayerPriority::EnvVars, config)
    }

    /// Create a CLI layer.
    pub fn cli_layer(config: Config) -> Self {
        Self::new("cli", LayerPriority::Cli, config)
    }
}

/// Strategy for merging values from different layers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum MergeStrategy {
    /// Higher priority overrides lower priority.
    #[default]
    Override,
    /// Lower priority overrides higher priority.
    Underride,
    /// Deep merge objects, override primitives.
    DeepMerge,
    /// Append arrays.
    AppendArrays,
}

/// Layer stack - manages multiple configuration layers.
#[derive(Debug, Default)]
pub struct LayerStack {
    layers: Vec<Layer>,
    strategy: MergeStrategy,
}

impl LayerStack {
    /// Create a new layer stack.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create with a merge strategy.
    pub fn with_strategy(strategy: MergeStrategy) -> Self {
        Self { layers: Vec::new(), strategy }
    }

    /// Add a layer.
    pub fn add_layer(&mut self, layer: Layer) {
        self.layers.push(layer);
        self.layers.sort_by_key(|a| a.priority);
    }

    /// Add a layer from a config with priority.
    pub fn add(&mut self, name: impl Into<String>, priority: LayerPriority, config: Config) {
        self.add_layer(Layer::new(name, priority, config));
    }

    /// Merge all layers into a single config.
    pub fn merge(&self) -> Config {
        let mut result = Config::new();

        for layer in &self.layers {
            match self.strategy {
                MergeStrategy::Override => {
                    result.merge(&layer.config);
                }
                MergeStrategy::Underride => {
                    let mut merged = layer.config.clone();
                    merged.merge(&result);
                    result = merged;
                }
                MergeStrategy::DeepMerge => {
                    result.merge(&layer.config);
                }
                MergeStrategy::AppendArrays => {
                    result.merge(&layer.config);
                }
            }
        }

        result
    }

    /// Get the number of layers.
    pub fn len(&self) -> usize {
        self.layers.len()
    }

    /// Check if empty.
    pub fn is_empty(&self) -> bool {
        self.layers.is_empty()
    }

    /// Return layers in merge order.
    pub fn layers(&self) -> &[Layer] {
        &self.layers
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_layer_priority() {
        assert!(LayerPriority::Cli > LayerPriority::EnvVars);
        assert!(LayerPriority::EnvVars > LayerPriority::Local);
        assert!(LayerPriority::Local > LayerPriority::Default);
    }

    #[test]
    fn test_layer_stack_merge() {
        let mut stack = LayerStack::new();

        let mut default = Config::new();
        default.set("a", 1);
        default.set("b", "default");
        stack.add_layer(Layer::default_layer(default));

        let mut cli = Config::new();
        cli.set("b", "cli");
        cli.set("c", 3);
        stack.add_layer(Layer::cli_layer(cli));

        let merged = stack.merge();
        assert_eq!(merged.get_typed::<i32>("a").unwrap(), 1);
        assert_eq!(merged.get_typed::<String>("b").unwrap(), "cli");
        assert_eq!(merged.get_typed::<i32>("c").unwrap(), 3);
    }
}
