//! Logger Builder

use crate::domain::{Level, LogEntry, LogError, Logger};
use async_trait::async_trait;
use std::sync::Arc;
use parking_lot::RwLock;

pub struct LoggerBuilder {
    name: String,
    level: Level,
}

impl LoggerBuilder {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            level: Level::Info,
        }
    }

    pub fn level(mut self, level: Level) -> Self {
        self.level = level;
        self
    }

    pub fn build(self) -> impl Logger {
        ConsoleLogger {
            name: self.name,
            level: self.level,
        }
    }
}

pub struct ConsoleLogger {
    name: String,
    level: Level,
}

#[async_trait]
impl Logger for ConsoleLogger {
    async fn log(&self, entry: LogEntry) -> Result<(), LogError> {
        if entry.level >= self.level {
            println!("[{}] {}: {}", entry.level, self.name, entry.message);
        }
        Ok(())
    }

    fn level(&self) -> Level {
        self.level
    }
}
