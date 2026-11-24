// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Sub-configuration structs for each domain.

use serde::{Deserialize, Serialize};

/// Cache configuration defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct CacheConfig {
    pub max_capacity: u64,
    pub ttl_secs: u64,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self { max_capacity: 10_000, ttl_secs: 300 }
    }
}

/// Runner configuration defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct RunnerConfig {
    pub timeout_secs: u64,
}

impl Default for RunnerConfig {
    fn default() -> Self {
        Self { timeout_secs: 30 }
    }
}

/// Scaling configuration defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct ScalingConfig {
    pub min_instances: u32,
    pub max_instances: u32,
    pub target_cpu_percent: f64,
    pub target_memory_percent: f64,
    pub scale_up_threshold: f64,
    pub scale_down_threshold: f64,
    pub cooldown_secs: u64,
}

impl Default for ScalingConfig {
    fn default() -> Self {
        Self {
            min_instances: 1,
            max_instances: 10,
            target_cpu_percent: 50.0,
            target_memory_percent: 70.0,
            scale_up_threshold: 0.8,
            scale_down_threshold: 0.3,
            cooldown_secs: 60,
        }
    }
}

/// Circuit breaker configuration defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct CircuitBreakerConfig {
    pub failure_threshold: u32,
    pub success_threshold: u32,
    pub retry_timeout_secs: u64,
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self { failure_threshold: 5, success_threshold: 3, retry_timeout_secs: 30 }
    }
}

/// Teammate default configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct TeammateConfig {
    pub max_concurrent: usize,
    pub timeout_secs: u64,
}

impl Default for TeammateConfig {
    fn default() -> Self {
        Self { max_concurrent: 1, timeout_secs: 300 }
    }
}

/// Specification / rollback default configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct SpecConfig {
    pub default_version: String,
    pub default_timeout_secs: u32,
}

impl Default for SpecConfig {
    fn default() -> Self {
        Self { default_version: "1.0.0".to_string(), default_timeout_secs: 30 }
    }
}

/// Checkpoint / git signature configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct CheckpointConfig {
    pub git_signature_name: String,
    pub git_signature_email: String,
}

impl Default for CheckpointConfig {
    fn default() -> Self {
        Self {
            git_signature_name: "heliosHarness".to_string(),
            git_signature_email: "checkpoint@helios.local".to_string(),
        }
    }
}

/// Elicitation / intent classification configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct ElicitationConfig {
    pub confidence_threshold: f64,
}

impl Default for ElicitationConfig {
    fn default() -> Self {
        Self { confidence_threshold: 0.1 }
    }
}

/// Verification pipeline configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct VerifyConfig {
    pub test_timeout_secs: u64,
    pub smoke_test_timeout_secs: u64,
}

impl Default for VerifyConfig {
    fn default() -> Self {
        Self { test_timeout_secs: 300, smoke_test_timeout_secs: 60 }
    }
}

/// Predictive scaler configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct PredictiveScalerConfig {
    pub max_history: usize,
    pub prediction_horizon: usize,
}

impl Default for PredictiveScalerConfig {
    fn default() -> Self {
        Self { max_history: 100, prediction_horizon: 5 }
    }
}

/// Token bucket rate limiter configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct TokenBucketConfig {
    pub default_capacity: f64,
    pub default_refill_rate: f64,
}

impl Default for TokenBucketConfig {
    fn default() -> Self {
        Self { default_capacity: 100.0, default_refill_rate: 10.0 }
    }
}
