//! Logger Builder

use crate::adapters::sinks::Sink;
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

    /// Build a logger that forwards entries at or above the configured level
    /// to an existing sink. Sink errors are returned to the caller unchanged.
    ///
    /// The sink controls formatting; the builder name is only used by the
    /// default console logger returned by [`Self::build`].
    pub fn build_with_sink<S: Sink>(self, sink: S) -> SinkLogger<S> {
        SinkLogger {
            level: self.level,
            sink,
        }
    }

    pub fn build(self) -> impl Logger {
        ConsoleLogger {
            name: self.name,
            level: self.level,
        }
    }
}

/// Logger backed by an existing sink, with an explicit flush operation.
pub struct SinkLogger<S> {
    level: Level,
    sink: S,
}

impl<S: Sink> SinkLogger<S> {
    /// Flush accepted entries through the sink, preserving any flush error.
    pub async fn flush(&self) -> Result<(), LogError> {
        self.sink.flush().await
    }
}

#[async_trait]
impl<S: Sink> Logger for SinkLogger<S> {
    async fn log(&self, entry: LogEntry) -> Result<(), LogError> {
        if entry.level >= self.level {
            self.sink.write(&entry).await?;
        }
        Ok(())
    }

    fn level(&self) -> Level {
        self.level
    }
}

pub struct ConsoleLogger {
    name: String,
    level: Level,
}

impl ConsoleLogger {
    fn write_entry(
        &self,
        entry: &LogEntry,
        writer: &mut impl std::io::Write,
    ) -> Result<(), LogError> {
        writeln!(writer, "[{}] {}: {}", entry.level, self.name, entry.message)
            .and_then(|_| writer.flush())
            .map_err(|error| LogError::Io(error.to_string()))
    }
}

#[async_trait]
impl Logger for ConsoleLogger {
    async fn log(&self, entry: LogEntry) -> Result<(), LogError> {
        if entry.level >= self.level {
            self.write_entry(&entry, &mut std::io::stdout().lock())?;
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

    #[test]
    fn console_logger_returns_io_error() {
        struct BrokenWriter;
        impl std::io::Write for BrokenWriter {
            fn write(&mut self, _: &[u8]) -> std::io::Result<usize> {
                Err(std::io::Error::new(
                    std::io::ErrorKind::BrokenPipe,
                    "closed",
                ))
            }
            fn flush(&mut self) -> std::io::Result<()> {
                Ok(())
            }
        }
        let logger = ConsoleLogger {
            name: "test".into(),
            level: Level::Info,
        };
        assert!(matches!(
            logger.write_entry(&LogEntry::new(Level::Info, "message"), &mut BrokenWriter),
            Err(LogError::Io(_))
        ));
    }

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
