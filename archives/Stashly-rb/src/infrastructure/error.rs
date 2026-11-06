//! Infrastructure error handling.

use std::fmt;

#[derive(Debug)]
pub enum CacheKitError {
    Config(String),
    Init(String),
    Runtime(String),
}

impl fmt::Display for CacheKitError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CacheKitError::Config(msg) => write!(f, "Configuration error: {}", msg),
            CacheKitError::Init(msg) => write!(f, "Initialization error: {}", msg),
            CacheKitError::Runtime(msg) => write!(f, "Runtime error: {}", msg),
        }
    }
}

impl std::error::Error for CacheKitError {}
