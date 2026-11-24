//! Configuration source adapters.

use std::collections::HashMap;
use std::path::Path;

use async_trait::async_trait;

use crate::domain::{errors::ConfigError, sources::Source, Config, ConfigValue};

/// File-based configuration source.
pub struct FileSource {
    path: String,
}

impl FileSource {
    pub fn new(path: impl Into<String>) -> Self {
        Self { path: path.into() }
    }
}

#[async_trait]
impl Source for FileSource {
    fn name(&self) -> &str {
        "file"
    }

    fn is_available(&self) -> bool {
        Path::new(&self.path).exists()
    }

    async fn load(&self) -> Result<Config, ConfigError> {
        let content = tokio::fs::read_to_string(&self.path).await?;

        let extension = Path::new(&self.path).extension().and_then(|e| e.to_str()).unwrap_or("");

        let values: serde_json::Value = match extension {
            "toml" => {
                toml::from_str(&content).map_err(|e| ConfigError::ParseError(e.to_string()))?
            }
            "yaml" | "yml" => serde_yaml::from_str(&content)
                .map_err(|e| ConfigError::ParseError(e.to_string()))?,
            "json" => serde_json::from_str(&content)
                .map_err(|e| ConfigError::ParseError(e.to_string()))?,
            _ => return Err(ConfigError::ParseError(format!("Unknown extension: {extension}"))),
        };

        let values = flatten_json(values);
        let mut config = Config::new();
        for (key, value) in values {
            config.set(key, ConfigValue::from_json(&value));
        }

        Ok(config.with_source(self.path.clone()))
    }
}

/// Environment variable configuration source.
pub struct EnvSource {
    prefix: Option<String>,
}

impl EnvSource {
    pub fn new() -> Self {
        Self { prefix: None }
    }

    pub fn with_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.prefix = Some(prefix.into());
        self
    }
}

impl Default for EnvSource {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Source for EnvSource {
    fn name(&self) -> &str {
        "env"
    }

    async fn load(&self) -> Result<Config, ConfigError> {
        let mut config = Config::new();

        for (key, value) in std::env::vars() {
            if let Some(ref prefix) = self.prefix {
                if !key.starts_with(prefix) {
                    continue;
                }
                let key = key.strip_prefix(prefix).unwrap().to_string();
                let key = key.to_lowercase().replace('_', ".");
                config.set(key, value);
            } else {
                let key = key.to_lowercase().replace('_', ".");
                config.set(key, value);
            }
        }

        Ok(config.with_source("environment"))
    }
}

/// CLI arguments configuration source.
pub struct CliSource {
    args: Vec<(String, String)>,
}

impl CliSource {
    pub fn new() -> Self {
        Self { args: Vec::new() }
    }

    pub fn with_arg(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.args.push((key.into(), value.into()));
        self
    }
}

impl Default for CliSource {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl Source for CliSource {
    fn name(&self) -> &str {
        "cli"
    }

    async fn load(&self) -> Result<Config, ConfigError> {
        let mut config = Config::new();
        for (key, value) in &self.args {
            config.set(key, value.clone());
        }
        Ok(config.with_source("cli"))
    }
}

/// Flatten a nested JSON object into dot-notation keys.
fn flatten_json(value: serde_json::Value) -> HashMap<String, serde_json::Value> {
    fn flatten_recursive(
        value: &serde_json::Value,
        prefix: &str,
        result: &mut HashMap<String, serde_json::Value>,
    ) {
        match value {
            serde_json::Value::Object(map) => {
                for (key, val) in map {
                    let path =
                        if prefix.is_empty() { key.clone() } else { format!("{prefix}.{key}") };
                    flatten_recursive(val, &path, result);
                }
            }
            _ => {
                result.insert(prefix.to_string(), value.clone());
            }
        }
    }

    let mut result = HashMap::new();
    flatten_recursive(&value, "", &mut result);
    result
}
