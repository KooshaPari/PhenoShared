//! Format adapters for parsing configuration files.

use std::collections::HashMap;

use crate::domain::{errors::ConfigError, Config, ConfigValue};

/// TOML format parser.
pub struct TomlFormat;

impl TomlFormat {
    pub fn parse(&self, content: &str) -> Result<Config, ConfigError> {
        let value: toml::Value =
            toml::from_str(content).map_err(|e| ConfigError::ParseError(e.to_string()))?;

        let values: serde_json::Value =
            serde_json::to_value(value).map_err(|e| ConfigError::ParseError(e.to_string()))?;
        let mut config = Config::new();
        for (key, value) in flatten_json(values) {
            config.set(key, parse_value(&value));
        }
        Ok(config)
    }
}

/// YAML format parser.
pub struct YamlFormat;

impl YamlFormat {
    pub fn parse(&self, content: &str) -> Result<Config, ConfigError> {
        let value: serde_yaml::Value =
            serde_yaml::from_str(content).map_err(|e| ConfigError::ParseError(e.to_string()))?;

        let values = value_to_json(value);
        let mut config = Config::new();
        for (key, value) in flatten_json(values) {
            config.set(key, parse_value(&value));
        }
        Ok(config)
    }
}

/// JSON format parser.
pub struct JsonFormat;

impl JsonFormat {
    pub fn parse(&self, content: &str) -> Result<Config, ConfigError> {
        let value: serde_json::Value =
            serde_json::from_str(content).map_err(|e| ConfigError::ParseError(e.to_string()))?;

        let mut config = Config::new();
        for (key, value) in flatten_json(value) {
            config.set(key, parse_value(&value));
        }
        Ok(config)
    }
}

fn value_to_json(value: serde_yaml::Value) -> serde_json::Value {
    match value {
        serde_yaml::Value::Null => serde_json::Value::Null,
        serde_yaml::Value::Bool(b) => serde_json::Value::Bool(b),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                serde_json::Value::Number(i.into())
            } else if let Some(f) = n.as_f64() {
                serde_json::Number::from_f64(f)
                    .map(serde_json::Value::Number)
                    .unwrap_or(serde_json::Value::Null)
            } else {
                serde_json::Value::Null
            }
        }
        serde_yaml::Value::String(s) => serde_json::Value::String(s),
        serde_yaml::Value::Sequence(arr) => {
            serde_json::Value::Array(arr.into_iter().map(value_to_json).collect())
        }
        serde_yaml::Value::Mapping(map) => {
            let obj: serde_json::Map<String, serde_json::Value> = map
                .into_iter()
                .filter_map(|(k, v)| k.as_str().map(|k| (k.to_string(), value_to_json(v))))
                .collect();
            serde_json::Value::Object(obj)
        }
        serde_yaml::Value::Tagged(tagged) => value_to_json(tagged.value),
    }
}

fn parse_value(value: &serde_json::Value) -> ConfigValue {
    match value {
        serde_json::Value::Null => ConfigValue::Null,
        serde_json::Value::Bool(b) => ConfigValue::Bool(*b),
        serde_json::Value::Number(n) => ConfigValue::Number(n.as_f64().unwrap_or(0.0)),
        serde_json::Value::String(s) => ConfigValue::String(s.clone()),
        serde_json::Value::Array(arr) => ConfigValue::Array(arr.iter().map(parse_value).collect()),
        serde_json::Value::Object(map) => {
            ConfigValue::Object(map.iter().map(|(k, v)| (k.clone(), parse_value(v))).collect())
        }
    }
}

fn flatten_json(value: serde_json::Value) -> HashMap<String, serde_json::Value> {
    fn flatten_recursive(
        value: &serde_json::Value,
        prefix: &str,
        result: &mut HashMap<String, serde_json::Value>,
    ) {
        match value {
            serde_json::Value::Object(map) => {
                if map.is_empty() {
                    result.insert(prefix.to_string(), value.clone());
                } else {
                    for (key, val) in map {
                        let path =
                            if prefix.is_empty() { key.clone() } else { format!("{prefix}.{key}") };
                        flatten_recursive(val, &path, result);
                    }
                }
            }
            serde_json::Value::Array(arr) if arr.is_empty() => {
                result.insert(prefix.to_string(), value.clone());
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
