//! Logger Trait

use async_trait::async_trait;
use super::{Level, LogEntry};

#[async_trait]
pub trait Logger: Send + Sync {
    async fn log(&self, entry: LogEntry) -> Result<(), LogError>;
    fn level(&self) -> Level;
}

#[derive(Debug, Clone)]
pub enum LogError {
    Io(String),
    Serialization(String),
}

impl std::fmt::Display for LogError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LogError::Io(s) => write!(f, "IO error: {}", s),
            LogError::Serialization(s) => write!(f, "Serialization error: {}", s),
        }
    }
}

impl std::error::Error for LogError {}
