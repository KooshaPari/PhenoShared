// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Configuration error types.

use std::path::PathBuf;
use thiserror::Error;

/// Errors that can occur during configuration loading.
#[derive(Debug, Error)]
pub enum ConfigError {
    /// The config file could not be read.
    #[error("failed to read config file {path}: {inner}")]
    FileRead { path: PathBuf, inner: std::io::Error },

    /// The config file could not be parsed.
    #[error("failed to parse config file {path}: {inner}")]
    FileParse { path: PathBuf, inner: serde_yaml::Error },

    /// An environment variable had an invalid value.
    #[error("invalid value for env var {var}: {inner}")]
    EnvVar { var: String, inner: String },
}

/// Result alias for config operations.
pub type Result<T> = std::result::Result<T, ConfigError>;
