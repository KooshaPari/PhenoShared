//! Configuration loading utilities for the Phenotype ecosystem.
//!
//! Absorbed from `<REDACTED>/phenotype-config` per ADR-031 (L5-110).
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

use std::path::Path;

use serde::de::DeserializeOwned;
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
    use serde::Deserialize;

    use super::*;

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
}
