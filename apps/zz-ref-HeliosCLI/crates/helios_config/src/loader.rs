// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Configuration loading from files and environment variables.

use crate::error::{ConfigError, Result};
use crate::types::*;
use serde::de::Error as _;
use serde::{Deserialize, Serialize};
use std::env;
use std::path::PathBuf;

/// Top-level HeliosCLI configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct HeliosConfig {
    pub cache: CacheConfig,
    pub runner: RunnerConfig,
    pub scaling: ScalingConfig,
    pub circuit_breaker: CircuitBreakerConfig,
    pub teammate: TeammateConfig,
    pub spec: SpecConfig,
    pub checkpoint: CheckpointConfig,
    pub elicitation: ElicitationConfig,
    pub verify: VerifyConfig,
    pub predictive_scaler: PredictiveScalerConfig,
    pub token_bucket: TokenBucketConfig,
}

impl HeliosConfig {
    /// Load configuration from the default locations.
    pub fn load() -> Self {
        Self::load_from(None)
    }

    /// Load configuration, optionally specifying a config file path.
    pub fn load_from(config_path: Option<&std::path::Path>) -> Self {
        let mut config = HeliosConfig::default();

        if let Some(path) = config_path {
            if path.exists() {
                if let Ok(loaded) = Self::from_file(path) {
                    config = loaded;
                }
            }
        } else {
            let candidates = [
                PathBuf::from("helios.toml"),
                PathBuf::from("helios.yaml"),
                PathBuf::from("config/helios.toml"),
                PathBuf::from("config/helios.yaml"),
                PathBuf::from(".helios.toml"),
                PathBuf::from(".helios.yaml"),
            ];
            if let Ok(config_path_env) = env::var("HELIOS_CONFIG_PATH") {
                let p = PathBuf::from(&config_path_env);
                if p.exists() {
                    if let Ok(loaded) = Self::from_file(&p) {
                        config = loaded;
                    }
                }
            }
            for candidate in &candidates {
                if candidate.exists() {
                    if let Ok(loaded) = Self::from_file(candidate) {
                        config = loaded;
                    }
                    break;
                }
            }
        }

        config.apply_env_overrides();
        config
    }

    /// Parse config from a TOML or YAML file.
    pub fn from_file(path: &std::path::Path) -> Result<Self> {
        let contents = std::fs::read_to_string(path)
            .map_err(|e| ConfigError::FileRead { path: path.to_owned(), inner: e })?;

        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();

        match ext.as_str() {
            "yaml" | "yml" => serde_yaml::from_str(&contents)
                .map_err(|e| ConfigError::FileParse { path: path.to_owned(), inner: e }),
            "toml" => toml::from_str(&contents).map_err(|e| ConfigError::FileParse {
                path: path.to_owned(),
                inner: serde_yaml::Error::custom(e.to_string()),
            }),
            _ => serde_yaml::from_str(&contents).or_else(|_| {
                toml::from_str(&contents).map_err(|e| ConfigError::FileParse {
                    path: path.to_owned(),
                    inner: serde_yaml::Error::custom(e.to_string()),
                })
            }),
        }
    }

    /// Apply environment variable overrides.
    fn apply_env_overrides(&mut self) {
        self.cache.max_capacity =
            env_override("HELIOS_CACHE_MAX_CAPACITY", self.cache.max_capacity);
        self.cache.ttl_secs = env_override("HELIOS_CACHE_TTL", self.cache.ttl_secs);
        self.runner.timeout_secs = env_override("HELIOS_RUNNER_TIMEOUT", self.runner.timeout_secs);
        self.scaling.min_instances =
            env_override("HELIOS_SCALING_MIN_INSTANCES", self.scaling.min_instances);
        self.scaling.max_instances =
            env_override("HELIOS_SCALING_MAX_INSTANCES", self.scaling.max_instances);
        self.scaling.target_cpu_percent =
            env_override("HELIOS_SCALING_TARGET_CPU", self.scaling.target_cpu_percent);
        self.scaling.target_memory_percent =
            env_override("HELIOS_SCALING_TARGET_MEMORY", self.scaling.target_memory_percent);
        self.scaling.scale_up_threshold =
            env_override("HELIOS_SCALING_SCALE_UP", self.scaling.scale_up_threshold);
        self.scaling.scale_down_threshold =
            env_override("HELIOS_SCALING_SCALE_DOWN", self.scaling.scale_down_threshold);
        self.scaling.cooldown_secs =
            env_override("HELIOS_SCALING_COOLDOWN", self.scaling.cooldown_secs);
        self.circuit_breaker.failure_threshold =
            env_override("HELIOS_CB_FAILURE_THRESHOLD", self.circuit_breaker.failure_threshold);
        self.circuit_breaker.success_threshold =
            env_override("HELIOS_CB_SUCCESS_THRESHOLD", self.circuit_breaker.success_threshold);
        self.circuit_breaker.retry_timeout_secs =
            env_override("HELIOS_CB_RETRY_TIMEOUT", self.circuit_breaker.retry_timeout_secs);
        self.teammate.max_concurrent =
            env_override("HELIOS_TEAMMATE_MAX_CONCURRENT", self.teammate.max_concurrent);
        self.teammate.timeout_secs =
            env_override("HELIOS_TEAMMATE_TIMEOUT", self.teammate.timeout_secs);
        self.spec.default_version =
            env_override_string("HELIOS_SPEC_VERSION", &self.spec.default_version);
        self.spec.default_timeout_secs =
            env_override("HELIOS_SPEC_TIMEOUT", self.spec.default_timeout_secs);
        self.checkpoint.git_signature_name = env_override_string(
            "HELIOS_CHECKPOINT_SIGNATURE_NAME",
            &self.checkpoint.git_signature_name,
        );
        self.checkpoint.git_signature_email = env_override_string(
            "HELIOS_CHECKPOINT_SIGNATURE_EMAIL",
            &self.checkpoint.git_signature_email,
        );
        self.elicitation.confidence_threshold =
            env_override("HELIOS_ELICITATION_CONFIDENCE", self.elicitation.confidence_threshold);
        self.verify.test_timeout_secs =
            env_override("HELIOS_VERIFY_TEST_TIMEOUT", self.verify.test_timeout_secs);
        self.verify.smoke_test_timeout_secs =
            env_override("HELIOS_VERIFY_SMOKE_TIMEOUT", self.verify.smoke_test_timeout_secs);
    }
}

/// Parse an env var, falling back to the default.
fn env_override<T>(key: &str, default: T) -> T
where
    T: std::str::FromStr,
    <T as std::str::FromStr>::Err: std::fmt::Debug,
{
    match env::var(key) {
        Ok(val) => val.parse().unwrap_or_else(|_| {
            tracing::warn!("invalid value for {} (using default)", key);
            default
        }),
        Err(_) => default,
    }
}

/// Parse an env var as `String`, falling back to the default.
fn env_override_string(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}
