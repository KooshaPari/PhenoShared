//! Layered configuration provider using Figment.
//!
//! Loads `PhenoProcConfig` with the following precedence (later wins):
//!
//! 1. Built-in defaults (`PhenoProcConfig::default()`)
//! 2. Config file (TOML / YAML / JSON) — discovered via `PHENOPROC_CONFIG`
//!    env var, a well-known path, or an explicit path.
//! 3. Environment variables with prefix `PHENOPROC_`
//!
//! # Example
//!
//! ```rust,ignore
//! use phenotype_config_loader::figment_provider::PhenoProcConfigBuilder;
//!
//! let config = PhenoProcConfigBuilder::new()
//!     .with_file("phenoproc.toml")
//!     .load()
//!     .unwrap();
//! ```

use figment::providers::{Env, Format, Json, Toml, Yaml};
use figment::Figment;
use phenotype_config_core::PhenoProcConfig;
use serde::de::DeserializeOwned;

/// Error type for figment-based config loading.
#[derive(Debug, thiserror::Error)]
pub enum FigmentConfigError {
    #[error("Figment error: {0}")]
    Figment(#[from] figment::error::Error),

    #[error("Missing config file: {0}")]
    MissingFile(String),
}

/// Builder for loading `PhenoProcConfig` with figment layering.
///
/// Precedence (later overrides earlier):
/// 1. Built-in `PhenoProcConfig::default()`
/// 2. Config file if provided / discovered
/// 3. Environment variables `PHENOPROC_*`
#[derive(Debug)]
pub struct PhenoProcConfigBuilder {
    file_path: Option<String>,
    env_prefix: String,
}

impl Default for PhenoProcConfigBuilder {
    fn default() -> Self {
        Self::new()
    }
}

impl PhenoProcConfigBuilder {
    /// Create a new builder with default env prefix `PHENOPROC_`.
    pub fn new() -> Self {
        Self {
            file_path: None,
            env_prefix: "PHENOPROC_".to_string(),
        }
    }

    /// Set a specific config file path.
    ///
    /// The file format is auto-detected from the extension (`.toml`, `.yaml`,
    /// `.yml`, `.json`).
    pub fn with_file(mut self, path: impl Into<String>) -> Self {
        self.file_path = Some(path.into());
        self
    }

    /// Override the environment variable prefix (default: `PHENOPROC_`).
    pub fn with_env_prefix(mut self, prefix: impl Into<String>) -> Self {
        self.env_prefix = prefix.into();
        self
    }

    /// Load `PhenoProcConfig` using the configured sources.
    ///
    /// Layering order:
    /// 1. `PhenoProcConfig::default()` via serde JSON
    /// 2. Config file (if `with_file()` was called, or if `PHENOPROC_CONFIG`
    ///    env var is set)
    /// 3. `PHENOPROC_*` environment vars
    pub fn load(&self) -> Result<PhenoProcConfig, FigmentConfigError> {
        let mut figment = Figment::new()
            // Layer 1: built-in defaults
            .merge(Json::string(
                &serde_json::to_string(&PhenoProcConfig::default())
                    .expect("PhenoProcConfig defaults are always valid JSON"),
            ));

        // Layer 2: config file (explicit path or PHENOPROC_CONFIG env var)
        let config_path = self
            .file_path
            .clone()
            .or_else(|| std::env::var("PHENOPROC_CONFIG").ok());

        if let Some(ref path) = config_path {
            figment = figment.merge(figment_file_provider(path)?);
        }

        // Layer 3: environment variables with prefix
        let env_provider = Env::prefixed(&self.env_prefix)
            .ignore(&["CONFIG"]) // don't double-read PHENOPROC_CONFIG
            .map(|key| {
                // Convert PHENOPROC_POOL_DEFAULT_MEMORY_LIMIT_MB → pool_default_memory_limit_mb
                key.as_str()
                    .to_lowercase()
                    .to_string()
            });

        figment = figment.merge(env_provider);

        Ok(figment.extract::<PhenoProcConfig>()?)
    }

    /// Load any `DeserializeOwned` config from figment sources.
    ///
    /// Useful for loading configs other than `PhenoProcConfig`.
    pub fn load_custom<T: DeserializeOwned>(&self) -> Result<T, FigmentConfigError> {
        let mut figment = Figment::new();

        if let Some(ref path) = self.file_path {
            figment = figment.merge(figment_file_provider(path)?);
        }

        let env_provider = Env::prefixed(&self.env_prefix)
            .map(|key| key.as_str().to_lowercase().to_string());
        figment = figment.merge(env_provider);

        Ok(figment.extract::<T>()?)
    }
}

/// Convenience function: load `PhenoProcConfig` with defaults only.
pub fn load_defaults() -> PhenoProcConfig {
    PhenoProcConfig::default()
}

/// Convenience function: load `PhenoProcConfig` from a config file and
/// `PHENOPROC_*` environment variables.
pub fn load_phenoproc_config(path: Option<&str>) -> Result<PhenoProcConfig, FigmentConfigError> {
    let mut builder = PhenoProcConfigBuilder::new();
    if let Some(p) = path {
        builder = builder.with_file(p);
    }
    builder.load()
}

// ---------------------------------------------------------------------------
// Internal helper: detect file format and return figment provider
// ---------------------------------------------------------------------------

fn figment_file_provider(path: &str) -> Result<Box<dyn figment::Provider>, FigmentConfigError> {
    let lower = path.to_lowercase();
    if lower.ends_with(".toml") {
        Ok(Box::new(Toml::file(path)))
    } else if lower.ends_with(".yaml") || lower.ends_with(".yml") {
        Ok(Box::new(Yaml::file(path)))
    } else if lower.ends_with(".json") {
        Ok(Box::new(Json::file(path)))
    } else {
        Err(FigmentConfigError::MissingFile(format!(
            "unsupported config file format: {} (supported: .toml, .yaml, .yml, .json)",
            path
        )))
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_load_defaults() {
        let cfg = load_defaults();
        assert_eq!(cfg.pool_default_memory_limit_mb, 4096);
        assert_eq!(cfg.lock_default_ttl_secs, 300);
    }

    #[test]
    fn test_load_phenoproc_config_from_toml_file() {
        let toml_content = r#"
pool_default_memory_limit_mb = 8192
lock_default_ttl_secs = 600
"#;
        let mut file = tempfile::NamedTempFile::with_suffix(".toml").unwrap();
        write!(file, "{}", toml_content).unwrap();

        let cfg = load_phenoproc_config(Some(file.path().to_str().unwrap())).unwrap();
        assert_eq!(cfg.pool_default_memory_limit_mb, 8192);
        assert_eq!(cfg.lock_default_ttl_secs, 600);
        // Other fields should still have defaults
        assert_eq!(cfg.pool_default_max_processes, 100);
    }

    #[test]
    fn test_load_phenoproc_config_from_json_file() {
        let json_content = r#"{"pool_default_memory_limit_mb": 16384}"#;
        let mut file = tempfile::NamedTempFile::with_suffix(".json").unwrap();
        write!(file, "{}", json_content).unwrap();

        let cfg = load_phenoproc_config(Some(file.path().to_str().unwrap())).unwrap();
        assert_eq!(cfg.pool_default_memory_limit_mb, 16384);
        assert_eq!(cfg.shm_default_size, 4096); // default
    }

    #[test]
    fn test_load_phenoproc_config_from_yaml_file() {
        let yaml_content = "pool_default_memory_limit_mb: 32768\n";
        let mut file = tempfile::NamedTempFile::with_suffix(".yaml").unwrap();
        write!(file, "{}", yaml_content).unwrap();

        let cfg = load_phenoproc_config(Some(file.path().to_str().unwrap())).unwrap();
        assert_eq!(cfg.pool_default_memory_limit_mb, 32768);
    }

    #[test]
    fn test_load_phenoproc_config_no_file_uses_defaults() {
        // When no file is specified, should use defaults + env vars (which we avoid)
        let cfg = load_phenoproc_config(None).unwrap();
        assert!(cfg.is_default());
    }

    #[test]
    fn test_builder_custom_type() {
        #[derive(Debug, serde::Deserialize, PartialEq)]
        struct Custom {
            name: Option<String>,
            value: Option<i64>,
        }

        let toml = r#"name = "phenoproc""#;
        let mut file = tempfile::NamedTempFile::with_suffix(".toml").unwrap();
        write!(file, "{}", toml).unwrap();

        let builder = PhenoProcConfigBuilder::new()
            .with_file(file.path().to_str().unwrap());
        let cfg: Custom = builder.load_custom().unwrap();
        assert_eq!(cfg.name.as_deref(), Some("phenoproc"));
        assert_eq!(cfg.value, None);
    }

    #[test]
    fn test_env_override() {
        // Set an env var and verify it overrides the default
        std::env::set_var("PHENOPROC_POOL_DEFAULT_MEMORY_LIMIT_MB", "9999");

        let cfg = load_phenoproc_config(None).unwrap();
        assert_eq!(cfg.pool_default_memory_limit_mb, 9999);

        std::env::remove_var("PHENOPROC_POOL_DEFAULT_MEMORY_LIMIT_MB");
    }

    #[test]
    fn test_file_overrides_default_env_not_set() {
        // Without setting env vars, file values should override defaults
        let toml = r#"pool_default_max_processes = 50"#;
        let mut file = tempfile::NamedTempFile::with_suffix(".toml").unwrap();
        write!(file, "{}", toml).unwrap();

        let cfg = load_phenoproc_config(Some(file.path().to_str().unwrap())).unwrap();
        assert_eq!(cfg.pool_default_max_processes, 50);
    }

    #[test]
    fn test_unsupported_format_error() {
        let mut file = tempfile::NamedTempFile::with_suffix(".ini").unwrap();
        write!(file, "[section]\nkey=val").unwrap();

        let result = load_phenoproc_config(Some(file.path().to_str().unwrap()));
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(
            matches!(err, FigmentConfigError::MissingFile(_)),
            "expected MissingFile, got {:?}",
            err
        );
    }
}
