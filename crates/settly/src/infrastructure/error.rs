//! Infrastructure error handling.

use std::fmt;

/// ConfigKit-specific errors.
#[derive(Debug)]
pub enum ConfigKitError {
    /// Configuration error.
    Config(String),
    /// Initialization error.
    Init(String),
    /// Runtime error.
    Runtime(String),
    /// Shutdown error.
    Shutdown(String),
}

impl fmt::Display for ConfigKitError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConfigKitError::Config(msg) => write!(f, "Configuration error: {msg}"),
            ConfigKitError::Init(msg) => write!(f, "Initialization error: {msg}"),
            ConfigKitError::Runtime(msg) => write!(f, "Runtime error: {msg}"),
            ConfigKitError::Shutdown(msg) => write!(f, "Shutdown error: {msg}"),
        }
    }
}

impl std::error::Error for ConfigKitError {}
