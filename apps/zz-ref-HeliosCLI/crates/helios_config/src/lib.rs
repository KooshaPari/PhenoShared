// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Centralized configuration for HeliosCLI.
//!
//! Consolidates all magic numbers, default timeouts, ports, paths, and
//! thresholds that were previously hardcoded across individual crates into
//! a single `HeliosConfig` struct loaded from:
//!
//! 1. A config file (`helios.toml` or `helios.yaml` in the project root or
//!    a path pointed to by `HELIOS_CONFIG_PATH`).
//! 2. Environment variables prefixed with `HELIOS_` (e.g. `HELIOS_CACHE_TTL`).
//! 3. Sensible hardcoded defaults.
//!
//! # Example
//!
//! ```rust
//! use helios_config::HeliosConfig;
//!
//! let config = HeliosConfig::default();
//! assert_eq!(config.cache.max_capacity, 10_000);
//! assert_eq!(config.runner.timeout_secs, 30);
//! ```

pub mod error;
pub mod loader;
pub mod types;

pub use error::*;
pub use loader::*;
pub use types::*;

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;
    use std::path::PathBuf;

    /// Verify that the default configuration has expected values.
    #[test]
    fn test_default_config_values() {
        let config = HeliosConfig::default();
        assert_eq!(config.cache.max_capacity, 10_000);
        assert_eq!(config.cache.ttl_secs, 300);
        assert_eq!(config.runner.timeout_secs, 30);
        assert_eq!(config.scaling.min_instances, 1);
        assert_eq!(config.scaling.max_instances, 10);
        assert!((config.scaling.target_cpu_percent - 50.0).abs() < f64::EPSILON);
        assert_eq!(config.circuit_breaker.failure_threshold, 5);
        assert_eq!(config.circuit_breaker.success_threshold, 3);
        assert_eq!(config.teammate.max_concurrent, 1);
        assert_eq!(config.teammate.timeout_secs, 300);
        assert_eq!(config.spec.default_version, "1.0.0");
        assert_eq!(config.spec.default_timeout_secs, 30);
        assert_eq!(config.checkpoint.git_signature_name, "heliosHarness");
        assert_eq!(config.checkpoint.git_signature_email, "checkpoint@helios.local");
        assert!((config.elicitation.confidence_threshold - 0.1).abs() < f64::EPSILON);
        assert_eq!(config.verify.test_timeout_secs, 300);
        assert_eq!(config.verify.smoke_test_timeout_secs, 60);
    }

    #[test]
    fn test_config_roundtrip_yaml() {
        let config = HeliosConfig::default();
        let yaml = serde_yaml::to_string(&config).expect("serialize to yaml");
        let deserialized: HeliosConfig =
            serde_yaml::from_str(&yaml).expect("deserialize from yaml");
        assert_eq!(deserialized.cache.max_capacity, config.cache.max_capacity);
        assert_eq!(deserialized.runner.timeout_secs, config.runner.timeout_secs);
        assert_eq!(
            deserialized.checkpoint.git_signature_name,
            config.checkpoint.git_signature_name
        );
    }

    #[test]
    fn test_config_partial_overlay() {
        let partial_yaml = r#"
cache:
  max_capacity: 5000
runner:
  timeout_secs: 60
"#;
        let partial: HeliosConfig =
            serde_yaml::from_str(partial_yaml).expect("deserialize partial config");
        assert_eq!(partial.cache.max_capacity, 5000);
        assert_eq!(partial.runner.timeout_secs, 60);
        assert_eq!(partial.cache.ttl_secs, 300);
        assert_eq!(partial.scaling.min_instances, 1);
        assert_eq!(partial.teammate.timeout_secs, 300);
    }

    #[test]
    fn test_config_from_yaml_file() {
        let dir = std::env::temp_dir();
        let path = dir.join("helios_test_config.yaml");
        let yaml_content = r#"
cache:
  max_capacity: 7777
  ttl_secs: 600
runner:
  timeout_secs: 120
"#;
        std::fs::write(&path, yaml_content).expect("write test config");
        let config = HeliosConfig::from_file(&path).expect("load from file");
        assert_eq!(config.cache.max_capacity, 7777);
        assert_eq!(config.cache.ttl_secs, 600);
        assert_eq!(config.runner.timeout_secs, 120);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn test_config_from_toml_file() {
        let dir = std::env::temp_dir();
        let path = dir.join("helios_test_config.toml");
        let toml_content = r#"
[cache]
max_capacity = 4242
[runner]
timeout_secs = 99
"#;
        std::fs::write(&path, toml_content).expect("write test config");
        let config = HeliosConfig::from_file(&path).expect("load from toml");
        assert_eq!(config.cache.max_capacity, 4242);
        assert_eq!(config.runner.timeout_secs, 99);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn test_load_from_explicit_path_overrides_defaults() {
        let dir = std::env::temp_dir();
        let path = dir.join("helios_load_from_test.yaml");
        let yaml_content = r#"
cache:
  max_capacity: 1111
"#;
        std::fs::write(&path, yaml_content).expect("write test config");
        let config = HeliosConfig::load_from(Some(&path));
        assert_eq!(config.cache.max_capacity, 1111);
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn test_env_overrides_apply_on_load() {
        let key = "HELIOS_CACHE_MAX_CAPACITY";
        let prior = env::var(key).ok();
        env::set_var(key, "9090");
        let config = HeliosConfig::load();
        assert_eq!(config.cache.max_capacity, 9090);
        match prior {
            Some(value) => env::set_var(key, value),
            None => env::remove_var(key),
        }
    }

    #[test]
    fn config_error_file_read_display() {
        let err = ConfigError::FileRead {
            path: PathBuf::from("/bad/config.yaml"),
            inner: std::io::Error::new(std::io::ErrorKind::NotFound, "not found"),
        };
        let msg = err.to_string();
        assert!(msg.contains("/bad/config.yaml"));
        assert!(msg.contains("not found"));
    }

    #[test]
    fn config_error_env_var_display() {
        let err = ConfigError::EnvVar { var: "HELIOS_FOO".into(), inner: "not a number".into() };
        let msg = err.to_string();
        assert!(msg.contains("HELIOS_FOO"));
        assert!(msg.contains("not a number"));
    }

    #[test]
    fn load_from_nonexistent_path_uses_defaults() {
        let path = std::path::Path::new("/nonexistent/helios_config_test.yaml");
        let config = HeliosConfig::load_from(Some(path));
        assert_eq!(config.cache.max_capacity, 10_000);
        assert_eq!(config.runner.timeout_secs, 30);
    }

    #[test]
    fn load_from_none_uses_defaults() {
        let prior = env::var("HELIOS_CONFIG_PATH").ok();
        env::remove_var("HELIOS_CONFIG_PATH");
        let config = HeliosConfig::load_from(None);
        assert_eq!(config.cache.max_capacity, 10_000);
        if let Some(value) = prior {
            env::set_var("HELIOS_CONFIG_PATH", value);
        }
    }

    #[test]
    fn test_config_roundtrip_toml() {
        let config = HeliosConfig::default();
        let toml_str = toml::to_string(&config).expect("serialize to toml");
        let deserialized: HeliosConfig = toml::from_str(&toml_str).expect("deserialize from toml");
        assert_eq!(deserialized.cache.max_capacity, config.cache.max_capacity);
        assert_eq!(deserialized.runner.timeout_secs, config.runner.timeout_secs);
        assert_eq!(
            deserialized.checkpoint.git_signature_email,
            config.checkpoint.git_signature_email
        );
    }

    #[test]
    fn test_scaling_config_defaults() {
        let cfg = ScalingConfig::default();
        assert_eq!(cfg.min_instances, 1);
        assert_eq!(cfg.max_instances, 10);
        assert!((cfg.target_cpu_percent - 50.0).abs() < f64::EPSILON);
        assert!((cfg.target_memory_percent - 70.0).abs() < f64::EPSILON);
        assert!((cfg.scale_up_threshold - 0.8).abs() < f64::EPSILON);
        assert!((cfg.scale_down_threshold - 0.3).abs() < f64::EPSILON);
        assert_eq!(cfg.cooldown_secs, 60);
    }

    #[test]
    fn test_predictive_scaler_defaults() {
        let cfg = PredictiveScalerConfig::default();
        assert_eq!(cfg.max_history, 100);
        assert_eq!(cfg.prediction_horizon, 5);
    }

    #[test]
    fn test_token_bucket_defaults() {
        let cfg = TokenBucketConfig::default();
        assert!((cfg.default_capacity - 100.0).abs() < f64::EPSILON);
        assert!((cfg.default_refill_rate - 10.0).abs() < f64::EPSILON);
    }

    #[test]
    fn test_elicitation_config_defaults() {
        let cfg = ElicitationConfig::default();
        assert!((cfg.confidence_threshold - 0.1).abs() < f64::EPSILON);
    }

    #[test]
    fn test_verify_config_defaults() {
        let cfg = VerifyConfig::default();
        assert_eq!(cfg.test_timeout_secs, 300);
        assert_eq!(cfg.smoke_test_timeout_secs, 60);
    }

    #[test]
    fn test_circuit_breaker_config_defaults() {
        let cfg = CircuitBreakerConfig::default();
        assert_eq!(cfg.failure_threshold, 5);
        assert_eq!(cfg.success_threshold, 3);
        assert_eq!(cfg.retry_timeout_secs, 30);
    }

    #[test]
    fn test_teammate_config_defaults() {
        let cfg = TeammateConfig::default();
        assert_eq!(cfg.max_concurrent, 1);
        assert_eq!(cfg.timeout_secs, 300);
    }

    #[test]
    fn test_spec_config_defaults() {
        let cfg = SpecConfig::default();
        assert_eq!(cfg.default_version, "1.0.0");
        assert_eq!(cfg.default_timeout_secs, 30);
    }

    #[test]
    fn test_checkpoint_config_defaults() {
        let cfg = CheckpointConfig::default();
        assert_eq!(cfg.git_signature_name, "heliosHarness");
        assert_eq!(cfg.git_signature_email, "checkpoint@helios.local");
    }

    #[test]
    fn test_env_override_string_fields() {
        let name_key = "HELIOS_CHECKPOINT_SIGNATURE_NAME";
        let email_key = "HELIOS_CHECKPOINT_SIGNATURE_EMAIL";
        let prior_name = env::var(name_key).ok();
        let prior_email = env::var(email_key).ok();
        env::set_var(name_key, "test-author");
        env::set_var(email_key, "test@example.com");

        let config = HeliosConfig::load();
        assert_eq!(config.checkpoint.git_signature_name, "test-author");
        assert_eq!(config.checkpoint.git_signature_email, "test@example.com");

        match prior_name {
            Some(v) => env::set_var(name_key, v),
            None => env::remove_var(name_key),
        }
        match prior_email {
            Some(v) => env::set_var(email_key, v),
            None => env::remove_var(email_key),
        }
    }
}
