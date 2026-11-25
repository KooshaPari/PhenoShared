//! Configuration entity and value objects.

use std::collections::HashMap;
use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

use super::errors::ConfigError;

/// A dot-notation path into the configuration.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct ConfigPath(String);

impl ConfigPath {
    /// Create a new path from a dot-notation string.
    pub fn new(path: impl Into<String>) -> Self {
        Self(path.into())
    }

    /// Get the path segments.
    pub fn segments(&self) -> Vec<&str> {
        self.0.split('.').collect()
    }

    /// Get the parent path.
    pub fn parent(&self) -> Option<ConfigPath> {
        self.0.rsplit_once('.').map(|(p, _)| ConfigPath(p.to_string()))
    }

    /// Get the key (last segment).
    pub fn key(&self) -> &str {
        self.0.rsplit_once('.').map(|(_, k)| k).unwrap_or(&self.0)
    }
}

impl fmt::Display for ConfigPath {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl FromStr for ConfigPath {
    type Err = std::convert::Infallible;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(Self::new(s))
    }
}

/// A configuration value with type information.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(untagged)]
pub enum ConfigValue {
    #[default]
    Null,
    Bool(bool),
    Number(f64),
    String(String),
    Array(Vec<ConfigValue>),
    Object(HashMap<String, ConfigValue>),
}

impl ConfigValue {
    /// Convert from a JSON value.
    pub fn from_json(value: &serde_json::Value) -> Self {
        match value {
            serde_json::Value::Null => ConfigValue::Null,
            serde_json::Value::Bool(b) => ConfigValue::Bool(*b),
            serde_json::Value::Number(n) => ConfigValue::Number(n.as_f64().unwrap_or(0.0)),
            serde_json::Value::String(s) => ConfigValue::String(s.clone()),
            serde_json::Value::Array(items) => {
                ConfigValue::Array(items.iter().map(Self::from_json).collect())
            }
            serde_json::Value::Object(map) => ConfigValue::Object(
                map.iter().map(|(k, v)| (k.clone(), Self::from_json(v))).collect(),
            ),
        }
    }

    /// Get a nested value by path.
    pub fn get(&self, path: &ConfigPath) -> Option<&ConfigValue> {
        let mut current = self;
        for segment in path.segments() {
            match current {
                ConfigValue::Object(map) => {
                    current = map.get(segment)?;
                }
                _ => return None,
            }
        }
        Some(current)
    }

    /// Set a nested value by path.
    pub fn set(&mut self, path: &ConfigPath, value: ConfigValue) {
        let segments = path.segments();
        if segments.is_empty() {
            return;
        }

        // Navigate to the parent
        let mut current = self;
        for segment in &segments[..segments.len() - 1] {
            match current {
                ConfigValue::Object(map) => {
                    current = map
                        .entry((*segment).to_string())
                        .or_insert_with(|| ConfigValue::Object(HashMap::new()));
                }
                _ => return,
            }
        }

        // Set the value
        if let ConfigValue::Object(map) = current {
            if let Some(last) = segments.last() {
                map.insert(last.to_string(), value);
            }
        }
    }

    /// Get as a specific type.
    pub fn as_type<T: FromStr>(&self) -> Option<T> {
        match self {
            ConfigValue::String(s) => s.parse().ok(),
            ConfigValue::Bool(b) => b.to_string().parse().ok(),
            ConfigValue::Number(n) => n.to_string().parse().ok(),
            _ => None,
        }
    }

    /// Check if this is null.
    pub fn is_null(&self) -> bool {
        matches!(self, ConfigValue::Null)
    }

    /// Convert to JSON string.
    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_default()
    }
}

impl From<bool> for ConfigValue {
    fn from(b: bool) -> Self {
        ConfigValue::Bool(b)
    }
}

impl From<String> for ConfigValue {
    fn from(s: String) -> Self {
        ConfigValue::String(s)
    }
}

impl From<&str> for ConfigValue {
    fn from(s: &str) -> Self {
        ConfigValue::String(s.to_string())
    }
}

macro_rules! impl_from_numeric {
    ($($ty:ty),* $(,)?) => {
        $(
            impl From<$ty> for ConfigValue {
                fn from(n: $ty) -> Self {
                    ConfigValue::Number(n as f64)
                }
            }
        )*
    };
}

impl_from_numeric!(i8, i16, i32, i64, isize, u8, u16, u32, u64, usize, f32, f64);

/// Configuration entity - the root of all configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Configuration values.
    values: HashMap<String, ConfigValue>,
    /// Metadata about the config source.
    source: Option<String>,
}

impl Config {
    /// Create a new empty configuration.
    pub fn new() -> Self {
        Self { values: HashMap::new(), source: None }
    }

    /// Create from a values map.
    pub fn from_values(values: HashMap<String, ConfigValue>) -> Self {
        Self { values, source: None }
    }

    /// Create with a source name.
    pub fn with_source(mut self, source: impl Into<String>) -> Self {
        self.source = Some(source.into());
        self
    }

    /// Get a value by key.
    pub fn get(&self, key: &str) -> Option<&ConfigValue> {
        self.values.get(key)
    }

    /// Set a value by key.
    pub fn set(&mut self, key: impl Into<String>, value: impl Into<ConfigValue>) {
        self.values.insert(key.into(), value.into());
    }

    /// Check if a key exists.
    pub fn contains_key(&self, key: &str) -> bool {
        self.values.contains_key(key)
    }

    /// Get all keys.
    pub fn keys(&self) -> impl Iterator<Item = &str> {
        self.values.keys().map(|s| s.as_str())
    }

    /// Merge another config into this one.
    pub fn merge(&mut self, other: &Config) {
        for (key, value) in &other.values {
            if let Some(existing) = self.values.get_mut(key) {
                if let ConfigValue::Object(existing_map) = existing {
                    if let ConfigValue::Object(other_map) = value {
                        for (k, v) in other_map {
                            existing_map.insert(k.clone(), v.clone());
                        }
                        continue;
                    }
                }
                *existing = value.clone();
            } else {
                self.values.insert(key.clone(), value.clone());
            }
        }
    }

    /// Get as a typed value.
    pub fn get_typed<T: FromStr>(&self, key: &str) -> Result<T, ConfigError> {
        self.get(key)
            .and_then(|v| v.as_type())
            .ok_or_else(|| ConfigError::KeyNotFound(key.to_string()))
    }
}

impl Default for Config {
    fn default() -> Self {
        Self::new()
    }
}

impl From<HashMap<String, ConfigValue>> for Config {
    fn from(values: HashMap<String, ConfigValue>) -> Self {
        Self::from_values(values)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_path() {
        let path = ConfigPath::new("database.host");
        assert_eq!(path.segments(), vec!["database", "host"]);
        assert_eq!(path.key(), "host");
        assert_eq!(path.parent(), Some(ConfigPath::new("database")));
    }

    #[test]
    fn test_config_value_get_set() {
        let mut value = ConfigValue::Object(HashMap::new());
        value.set(&ConfigPath::new("database.host"), "localhost".into());

        assert_eq!(
            value.get(&ConfigPath::new("database.host")),
            Some(&ConfigValue::String("localhost".to_string()))
        );
    }

    #[test]
    fn test_config_merge() {
        let mut config1 = Config::new();
        config1.set("a", 1);
        config1.set("b", "original");

        let mut config2 = Config::new();
        config2.set("b", "override");
        config2.set("c", 3);

        config1.merge(&config2);

        assert_eq!(config1.get_typed::<i32>("a").unwrap(), 1);
        assert_eq!(config1.get_typed::<String>("b").unwrap(), "override");
        assert_eq!(config1.get_typed::<i32>("c").unwrap(), 3);
    }
}
