use async_trait::async_trait;
use logkit::adapters::sinks::{BoundedSink, Sink};
use logkit::{Level, LogEntry, LogError, Logger, LoggerBuilder};
use std::sync::{Arc, Mutex};

#[derive(Clone, Default)]
struct RecordingSink(Arc<Mutex<Vec<String>>>);

#[async_trait]
impl Sink for RecordingSink {
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError> {
        self.0.lock().unwrap().push(entry.message.clone());
        Ok(())
    }
}

#[tokio::test]
async fn public_builder_routes_filtered_entries_through_bounded_sink() {
    let sink = RecordingSink::default();
    let logger = LoggerBuilder::new("consumer")
        .level(Level::Warn)
        .build_with_sink(BoundedSink::new(sink.clone(), 1));
    logger
        .log(LogEntry::new(Level::Info, "filtered"))
        .await
        .unwrap();
    logger
        .log(LogEntry::new(Level::Warn, "retained"))
        .await
        .unwrap();
    assert_eq!(*sink.0.lock().unwrap(), vec!["retained"]);
    assert_eq!(logger.level(), Level::Warn);
}

struct FailedSink;

#[async_trait]
impl Sink for FailedSink {
    async fn write(&self, _: &LogEntry) -> Result<(), LogError> {
        Err(LogError::Io("sink unavailable".into()))
    }
}

#[tokio::test]
async fn public_builder_returns_sink_failure_without_reporting_success() {
    let logger = LoggerBuilder::new("consumer").build_with_sink(FailedSink);
    assert!(matches!(
        logger.log(LogEntry::new(Level::Error, "failure")).await,
        Err(LogError::Io(message)) if message == "sink unavailable"
    ));
    assert!(logger
        .log(LogEntry::new(Level::Debug, "filtered"))
        .await
        .is_ok());
}

#[derive(Clone, Default)]
struct BufferedSink {
    pending: Arc<Mutex<Vec<String>>>,
    delivered: Arc<Mutex<Vec<String>>>,
}

#[async_trait]
impl Sink for BufferedSink {
    async fn write(&self, entry: &LogEntry) -> Result<(), LogError> {
        self.pending.lock().unwrap().push(entry.message.clone());
        Ok(())
    }
    async fn flush(&self) -> Result<(), LogError> {
        self.delivered
            .lock()
            .unwrap()
            .extend(self.pending.lock().unwrap().drain(..));
        Ok(())
    }
}

#[tokio::test]
async fn public_sink_logger_flush_delivers_buffered_entries() {
    let sink = BufferedSink::default();
    let logger = LoggerBuilder::new("buffered").build_with_sink(sink.clone());
    logger
        .log(LogEntry::new(Level::Info, "pending"))
        .await
        .unwrap();
    assert!(sink.delivered.lock().unwrap().is_empty());
    logger.flush().await.unwrap();
    assert_eq!(*sink.delivered.lock().unwrap(), vec!["pending"]);
    assert!(sink.pending.lock().unwrap().is_empty());
}

struct FailedFlushSink;
#[async_trait]
impl Sink for FailedFlushSink {
    async fn write(&self, _: &LogEntry) -> Result<(), LogError> {
        Ok(())
    }
    async fn flush(&self) -> Result<(), LogError> {
        Err(LogError::Io("flush unavailable".into()))
    }
}

#[tokio::test]
async fn public_sink_logger_preserves_flush_error() {
    let logger = LoggerBuilder::new("flush error").build_with_sink(FailedFlushSink);
    assert!(matches!(logger.flush().await, Err(LogError::Io(s)) if s == "flush unavailable"));
}
