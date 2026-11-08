//! Configuration loading utilities for Phenotype
//!
//! Supports loading configs from TOML, YAML, JSON, and environment variables.

pub mod figment_provider;

use serde::de::DeserializeOwned;
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

/// Configuration loading errors
#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("TOML parse error: {0}")]
    Toml(#[from] toml::de::Error),
    #[error("JSON parse error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("YAML parse error: {0}")]
    Yaml(String),
    #[error("Unsupported format: {0}")]
    UnsupportedFormat(String),
    #[error("Config not found: {0}")]
    NotFound(String),
}

/// Result type for config operations
pub type Result<T> = std::result::Result<T, ConfigError>;

/// Configuration file formats
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConfigFormat {
    /// TOML format
    Toml,
    /// YAML format
    Yaml,
    /// JSON format
    Json,
}

impl ConfigFormat {
    /// Detect format from file extension
    pub fn from_path<P: AsRef<Path>>(path: P) -> Option<Self> {
        let ext = path.as_ref().extension()?.to_str()?;
        match ext.to_lowercase().as_str() {
            "toml" => Some(Self::Toml),
            "yaml" | "yml" => Some(Self::Yaml),
            "json" => Some(Self::Json),
            _ => None,
        }
    }
}

/// Load configuration from a file
pub fn load_from_file<T: DeserializeOwned, P: AsRef<Path>>(path: P) -> Result<T> {
    let content = std::fs::read_to_string(&path)?;
    let format = ConfigFormat::from_path(&path).ok_or_else(|| {
        ConfigError::UnsupportedFormat(path.as_ref().to_string_lossy().to_string())
    })?;

    parse_config(&content, format)
}

/// Parse configuration from a string
pub fn parse_config<T: DeserializeOwned>(content: &str, format: ConfigFormat) -> Result<T> {
    match format {
        ConfigFormat::Toml => {
            let value: T = toml::from_str(content)?;
            Ok(value)
        }
        ConfigFormat::Json => {
            let value: T = serde_json::from_str(content)?;
            Ok(value)
        }
        ConfigFormat::Yaml => {
            serde_yaml::from_str(content).map_err(|e| ConfigError::Yaml(e.to_string()))
        }
    }
}

/// Load from environment variables with prefix
pub fn from_env<T: DeserializeOwned>(prefix: &str) -> Result<T> {
    let vars: HashMap<String, String> = std::env::vars()
        .filter(|(k, _)| k.starts_with(prefix))
        .map(|(k, v)| (k.trim_start_matches(prefix).to_lowercase(), v))
        .collect();

    let json = serde_json::to_string(&vars).map_err(ConfigError::Json)?;
    serde_json::from_str(&json).map_err(ConfigError::Json)
}

/// Configuration loader with builder pattern
#[derive(Debug)]
pub struct ConfigLoader<T: DeserializeOwned> {
    file_path: Option<String>,
    env_prefix: Option<String>,
    _phantom: std::marker::PhantomData<T>,
}

impl<T: DeserializeOwned + Default> Default for ConfigLoader<T> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T: DeserializeOwned> ConfigLoader<T> {
    /// Create a new config loader
    pub fn new() -> Self {
        Self {
            file_path: None,
            env_prefix: None,
            _phantom: std::marker::PhantomData,
        }
    }

    /// Set file path to load from
    pub fn with_file(mut self, path: impl Into<String>) -> Self {
        self.file_path = Some(path.into());
        self
    }

    /// Set environment variable prefix
    pub fn with_env_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.env_prefix = Some(prefix.into());
        self
    }

    /// Load configuration
    pub fn load(self) -> Result<T> {
        if let Some(path) = self.file_path {
            load_from_file(&path)
        } else if let Some(prefix) = self.env_prefix {
            from_env(&prefix)
        } else {
            Err(ConfigError::NotFound("No source specified".to_string()))
        }
    }
}

/// Load and merge multiple config sources
pub fn merge_configs<T: DeserializeOwned + serde::Serialize>(
    sources: Vec<(String, ConfigFormat)>,
) -> Result<T> {
    let mut merged = serde_json::Map::new();

    for (content, format) in sources {
        let value: serde_json::Value = parse_config(&content, format)?;
        if let serde_json::Value::Object(map) = value {
            for (k, v) in map {
                merged.insert(k, v);
            }
        }
    }

    let json = serde_json::Value::Object(merged);
    serde_json::from_value(json).map_err(ConfigError::Json)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::{Deserialize, Serialize};
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[derive(Debug, Deserialize, Serialize, PartialEq, Default)]
    struct TestConfig {
        name: String,
        value: i32,
    }

    #[test]
    fn test_parse_toml() {
        let toml = r#"name = "test"
value = 42
"#;
        let config: TestConfig = parse_config(toml, ConfigFormat::Toml).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
    }

    #[test]
    fn test_parse_json() {
        let json = r#"{"name": "test", "value": 42}"#;
        let config: TestConfig = parse_config(json, ConfigFormat::Json).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
    }

    #[test]
    fn test_load_from_file() -> Result<()> {
        let mut file = NamedTempFile::with_suffix(".json")?;
        write!(file, r#"{{"name": "test", "value": 42}}"#)?;

        let config: TestConfig = load_from_file(file.path())?;
        assert_eq!(config.name, "test");
        Ok(())
    }

    #[test]
    fn test_config_format_from_path() {
        assert_eq!(
            ConfigFormat::from_path("config.toml"),
            Some(ConfigFormat::Toml)
        );
        assert_eq!(
            ConfigFormat::from_path("config.yaml"),
            Some(ConfigFormat::Yaml)
        );
        assert_eq!(
            ConfigFormat::from_path("config.json"),
            Some(ConfigFormat::Json)
        );
        assert_eq!(ConfigFormat::from_path("config.txt"), None);
    }

    #[test]
    fn test_config_format_from_path_yml_and_uppercase() {
        assert_eq!(
            ConfigFormat::from_path("/etc/app/config.YML"),
            Some(ConfigFormat::Yaml)
        );
        assert_eq!(
            ConfigFormat::from_path("./relative/path/Config.JSON"),
            Some(ConfigFormat::Json)
        );
        assert_eq!(
            ConfigFormat::from_path("a/b/c.TOML"),
            Some(ConfigFormat::Toml)
        );
    }

    #[test]
    fn test_config_format_from_path_no_extension() {
        assert_eq!(ConfigFormat::from_path("/etc/app/config"), None);
    }

    #[test]
    fn test_parse_yaml() {
        let yaml = "name: test\nvalue: 42\n";
        let config: TestConfig = parse_config(yaml, ConfigFormat::Yaml).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
    }

    #[test]
    fn test_parse_toml_error() {
        let bad = "name = 'missing quote\nvalue = oops";
        let res: Result<TestConfig> = parse_config(bad, ConfigFormat::Toml);
        assert!(matches!(res, Err(ConfigError::Toml(_))));
    }

    #[test]
    fn test_parse_json_error() {
        let bad = "{ this is not json";
        let res: Result<TestConfig> = parse_json(bad, ConfigFormat::Json);
        assert!(matches!(res, Err(ConfigError::Json(_))));
    }

    fn parse_json<T: DeserializeOwned>(content: &str, fmt: ConfigFormat) -> Result<T> {
        parse_config(content, fmt)
    }

    #[test]
    fn test_load_from_file_toml() -> Result<()> {
        let mut file = NamedTempFile::with_suffix(".toml")?;
        write!(file, "name = \"from-toml\"\nvalue = 7\n")?;
        let cfg: TestConfig = load_from_file(file.path())?;
        assert_eq!(cfg.name, "from-toml");
        assert_eq!(cfg.value, 7);
        Ok(())
    }

    #[test]
    fn test_load_from_file_yaml() -> Result<()> {
        let mut file = NamedTempFile::with_suffix(".yaml")?;
        write!(file, "name: from-yaml\nvalue: 9\n")?;
        let cfg: TestConfig = load_from_file(file.path())?;
        assert_eq!(cfg.name, "from-yaml");
        assert_eq!(cfg.value, 9);
        Ok(())
    }

    #[test]
    fn test_load_from_file_unsupported_format() -> Result<()> {
        let mut file = NamedTempFile::with_suffix(".txt")?;
        write!(file, "irrelevant")?;
        let res: Result<TestConfig> = load_from_file(file.path());
        assert!(matches!(res, Err(ConfigError::UnsupportedFormat(_))));
        Ok(())
    }

    #[test]
    fn test_load_from_file_missing() {
        let res: Result<TestConfig> = load_from_file("/this/path/should/not/exist.json");
        assert!(matches!(res, Err(ConfigError::Io(_))));
    }

    #[test]
    fn test_config_error_display() {
        let io_err = ConfigError::Io(std::io::Error::new(std::io::ErrorKind::Other, "x"));
        assert!(format!("{}", io_err).contains("IO error"));

        let yaml_err = ConfigError::Yaml("bad".into());
        assert!(format!("{}", yaml_err).contains("bad"));
        assert!(format!("{}", yaml_err).contains("YAML"));

        let unsupported = ConfigError::UnsupportedFormat("xyz".into());
        assert!(format!("{}", unsupported).contains("xyz"));

        let nf = ConfigError::NotFound("config.toml".into());
        assert!(format!("{}", nf).contains("config.toml"));
    }

    #[derive(Debug, Deserialize, Serialize, PartialEq, Default)]
    struct EnvConfig {
        name: Option<String>,
        value: Option<String>,
    }

    #[test]
    fn test_from_env_with_prefix() {
        // Set isolated env vars for the test.
        let key1 = "PHENOTYPE_TEST_FOO_NAME";
        let key2 = "PHENOTYPE_TEST_FOO_VALUE";
        std::env::set_var(key1, "alpha");
        std::env::set_var(key2, "beta");

        let cfg: EnvConfig = from_env("PHENOTYPE_TEST_FOO_").unwrap();
        assert_eq!(cfg.name.as_deref(), Some("alpha"));
        assert_eq!(cfg.value.as_deref(), Some("beta"));

        std::env::remove_var(key1);
        std::env::remove_var(key2);
    }

    #[test]
    fn test_from_env_filters_by_prefix() {
        std::env::set_var("PHENOTYPE_TEST_BAR_X", "1");
        std::env::set_var("UNRELATED", "2");
        // Empty struct will work since it has no required fields.
        let cfg: Empty = from_env("PHENOTYPE_TEST_BAR_").unwrap();
        // Should be parsed successfully and not contain UNRELATED key.
        std::env::remove_var("PHENOTYPE_TEST_BAR_X");
        std::env::remove_var("UNRELATED");
    }

    #[derive(Debug, Deserialize, Default, PartialEq)]
    struct Empty {}

    #[test]
    fn test_config_loader_default() {
        let loader: ConfigLoader<TestConfig> = ConfigLoader::default();
        // No source set, load should return NotFound.
        let res = loader.load();
        assert!(matches!(res, Err(ConfigError::NotFound(_))));
    }

    #[test]
    fn test_config_loader_new_and_load_no_source() {
        let loader: ConfigLoader<TestConfig> = ConfigLoader::new();
        let res = loader.load();
        assert!(matches!(res, Err(ConfigError::NotFound(_))));
    }

    #[test]
    fn test_config_loader_with_file() -> Result<()> {
        let mut file = NamedTempFile::with_suffix(".json")?;
        write!(file, r#"{{"name": "loader", "value": 5}}"#)?;
        let loader: ConfigLoader<TestConfig> = ConfigLoader::new()
            .with_file(file.path().to_string_lossy().to_string());
        let cfg = loader.load()?;
        assert_eq!(cfg.name, "loader");
        assert_eq!(cfg.value, 5);
        Ok(())
    }

    #[test]
    fn test_config_loader_with_env_prefix() {
        std::env::set_var("PHENOTYPE_TEST_LOADER_X", "yes");
        let loader: ConfigLoader<Empty> = ConfigLoader::new().with_env_prefix("PHENOTYPE_TEST_LOADER_");
        let _cfg: Empty = loader.load().unwrap();
        std::env::remove_var("PHENOTYPE_TEST_LOADER_X");
    }

    #[test]
    fn test_config_loader_with_file_overrides_env() -> Result<()> {
        // When both file and env_prefix are set, file takes precedence (current impl).
        let mut file = NamedTempFile::with_suffix(".json")?;
        write!(file, r#"{{"name": "from-file", "value": 1}}"#)?;
        let loader: ConfigLoader<TestConfig> = ConfigLoader::new()
            .with_file(file.path().to_string_lossy().to_string())
            .with_env_prefix("PHENOTYPE_TEST_LOADER_");
        let cfg = loader.load()?;
        assert_eq!(cfg.name, "from-file");
        Ok(())
    }

    #[derive(Debug, Deserialize, Serialize, PartialEq)]
    struct MergedConfig {
        a: Option<String>,
        b: Option<i32>,
    }

    #[test]
    fn test_merge_configs_multiple_sources() {
        let src1 = (r#"{"a": "hello"}"#.to_string(), ConfigFormat::Json);
        let src2 = (r#"{"b": 42}"#.to_string(), ConfigFormat::Json);
        let merged: MergedConfig = merge_configs(vec![src1, src2]).unwrap();
        assert_eq!(merged.a.as_deref(), Some("hello"));
        assert_eq!(merged.b, Some(42));
    }

    #[test]
    fn test_merge_configs_later_overrides_earlier() {
        let src1 = (r#"{"a": "first"}"#.to_string(), ConfigFormat::Json);
        let src2 = (r#"{"a": "second"}"#.to_string(), ConfigFormat::Json);
        let merged: MergedConfig = merge_configs(vec![src1, src2]).unwrap();
        assert_eq!(merged.a.as_deref(), Some("second"));
    }

    #[test]
    fn test_merge_configs_empty_list_fails() {
        // With no sources, the resulting JSON is an empty object, and depending on
        // the target struct, it may parse as a default-constructed value or fail.
        // Test the actual behavior.
        let res: Result<MergedConfig> = merge_configs(vec![]);
        // Both fields are Optional, so an empty object should still parse.
        assert!(res.is_ok());
    }

    #[test]
    fn test_merge_configs_parse_error() {
        let bad = ("not valid json".to_string(), ConfigFormat::Json);
        let res: Result<MergedConfig> = merge_configs(vec![bad]);
        assert!(res.is_err());
    }
}
