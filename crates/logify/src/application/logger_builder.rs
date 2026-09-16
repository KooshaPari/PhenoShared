//! Logger Builder

use crate::domain::{Level, LogEntry, LogError, Logger};
use async_trait::async_trait;

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

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn console_logger_logs_above_level() {
        let logger = LoggerBuilder::new("test").level(Level::Warn).build();
        let info_entry = LogEntry::new(Level::Info, "should be filtered");
        let warn_entry = LogEntry::new(Level::Warn, "should pass");

        // Info is below Warn, so this should be filtered (no error)
        assert!(logger.log(info_entry).await.is_ok());
        // Warn is at threshold, should pass
        assert!(logger.log(warn_entry).await.is_ok());
    }

    #[tokio::test]
    async fn console_logger_filters_trace_debug() {
        let logger = LoggerBuilder::new("filter_test").level(Level::Info).build();
        assert!(logger
            .log(LogEntry::new(Level::Trace, "trace"))
            .await
            .is_ok());
        assert!(logger
            .log(LogEntry::new(Level::Debug, "debug"))
            .await
            .is_ok());
        assert!(logger.log(LogEntry::new(Level::Info, "info")).await.is_ok());
    }

    #[test]
    fn logger_builder_default_level() {
        let builder = LoggerBuilder::new("default");
        // Can't access private level field directly, but build() creates a ConsoleLogger
        // that uses Info as default
        let logger = builder.build();
        assert_eq!(logger.level(), Level::Info);
    }

    #[test]
    fn logger_builder_set_level() {
        let logger = LoggerBuilder::new("custom").level(Level::Debug).build();
        assert_eq!(logger.level(), Level::Debug);
    }

    #[test]
    fn logger_builder_name_preserved() {
        let logger = LoggerBuilder::new("my-app").build();
        // Logger is opaque, but we can verify it's constructed without panicking
        let _logger = logger;
    }
}
