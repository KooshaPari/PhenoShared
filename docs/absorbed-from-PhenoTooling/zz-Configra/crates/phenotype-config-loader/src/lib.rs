//! Configuration loading utilities for the Phenotype ecosystem.
//!
//! Absorbed from `KooshaPari/phenotype-config` per ADR-031 (L5-110).
//! This crate provides generic, type-safe JSON and TOML file loaders
//! that downstream consumers can use without depending on a heavier
//! configuration framework.
//!
//! # Examples
//!
//! ```no_run
//! use serde::Deserialize;
//! use std::path::Path;
//! use phenotype_config_loader::load_toml;
//!
//! #[derive(Deserialize, Debug)]
//! struct AppConfig {
//!     name: String,
//! }
//!
//! let cfg: AppConfig = load_toml(Path::new("app.toml")).unwrap();
//! println!("app = {}", cfg.name);
//! ```

use serde::de::DeserializeOwned;
use std::path::Path;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigLoadError {
    #[error("file not found: {0}")]
    NotFound(String),
    #[error("parse error: {0}")]
    Parse(String),
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
}

pub type Result<T> = std::result::Result<T, ConfigLoadError>;

/// Load and deserialize a JSON file at `path` into `T`.
///
/// # Errors
/// Returns `ConfigLoadError::Io` if the file cannot be read, or
/// `ConfigLoadError::Parse` if the file is not valid JSON or does not
/// match the target type.
pub fn load_json<T: DeserializeOwned>(path: &Path) -> Result<T> {
    let content = std::fs::read_to_string(path)?;
    serde_json::from_str::<T>(&content).map_err(|e| ConfigLoadError::Parse(e.to_string()))
}

/// Load and deserialize a TOML file at `path` into `T`.
///
/// # Errors
/// Returns `ConfigLoadError::Io` if the file cannot be read, or
/// `ConfigLoadError::Parse` if the file is not valid TOML or does not
/// match the target type.
pub fn load_toml<T: DeserializeOwned>(path: &Path) -> Result<T> {
    let content = std::fs::read_to_string(path)?;
    toml::from_str(&content).map_err(|e| ConfigLoadError::Parse(e.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde::Deserialize;

    #[derive(Deserialize, Debug, PartialEq)]
    struct TestConfig {
        name: String,
        value: i32,
    }

    #[test]
    fn test_load_json() {
        let dir = std::env::temp_dir();
        let path = dir.join("test_cfg.json");
        std::fs::write(&path, r#"{"name":"test","value":42}"#).unwrap();
        let config = load_json::<TestConfig>(&path).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn test_load_toml() {
        let dir = std::env::temp_dir();
        let path = dir.join("test_cfg.toml");
        std::fs::write(&path, "name = \"test\"\nvalue = 42").unwrap();
        let config = load_toml::<TestConfig>(&path).unwrap();
        assert_eq!(config.name, "test");
        assert_eq!(config.value, 42);
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn test_load_not_found() {
        let result = load_json::<TestConfig>(Path::new("/nonexistent.json"));
        assert!(result.is_err());
    }

    #[test]
    fn test_load_json_valid() {
        let dir = std::env::temp_dir();
        let path = dir.join("pheno_cfg_json_valid.json");
        std::fs::write(&path, r#"{"name":"valid","value":100}"#).unwrap();
        let config = load_json::<TestConfig>(&path).unwrap();
        assert_eq!(config.name, "valid");
        assert_eq!(config.value, 100);
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn test_load_json_invalid() {
        let dir = std::env::temp_dir();
        let path = dir.join("pheno_cfg_json_invalid.json");
        std::fs::write(&path, r#"{not valid json!!!}"#).unwrap();
        let result = load_json::<TestConfig>(&path);
        assert!(result.is_err());
        match result.unwrap_err() {
            ConfigLoadError::Parse(_) => {} // expected
            other => panic!("expected Parse error, got {:?}", other),
        }
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn test_load_toml_valid() {
        let dir = std::env::temp_dir();
        let path = dir.join("pheno_cfg_toml_valid.toml");
        std::fs::write(&path, "name = \"valid\"\nvalue = 200").unwrap();
        let config = load_toml::<TestConfig>(&path).unwrap();
        assert_eq!(config.name, "valid");
        assert_eq!(config.value, 200);
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn test_load_toml_invalid() {
        let dir = std::env::temp_dir();
        let path = dir.join("pheno_cfg_toml_invalid.toml");
        // Write something that looks like TOML but has a type mismatch
        std::fs::write(&path, "name = 123\nvalue = \"not-an-int\"").unwrap();
        let result = load_toml::<TestConfig>(&path);
        assert!(result.is_err());
        match result.unwrap_err() {
            ConfigLoadError::Parse(_) => {} // expected
            other => panic!("expected Parse error, got {:?}", other),
        }
        std::fs::remove_file(&path).ok();
    }
}
