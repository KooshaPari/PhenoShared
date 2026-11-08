//! Sinks

use crate::domain::{Level, LogEntry, LogError};
use async_trait::async_trait;

#[async_trait]
pub trait Sink: Send + Sync {
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError>;
    async fn flush(&self) -> Result<(), LogError>;
}

/// Console sink
pub struct ConsoleSink;

impl ConsoleSink {
    pub fn new() -> Self { Self }
}

impl Default for ConsoleSink {
    fn default() -> Self { Self::new() }
}

#[async_trait]
impl Sink for ConsoleSink {
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError> {
        if entry.level >= Level::Error {
            eprintln!("{} [{}]", entry.level, entry.message);
        } else {
            println!("{} [{}]", entry.level, entry.message);
        }
        Ok(())
    }

    async fn flush(&self) -> Result<(), LogError> {
        Ok(())
    }
}
