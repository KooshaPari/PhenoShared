use logkit::adapters::sinks::{BoundedSink, ConsoleSink};
use logkit::{Level, LogEntry, LogError, Logger, LoggerBuilder};

#[tokio::main]
async fn main() -> Result<(), LogError> {
    let logger = LoggerBuilder::new("consumer")
        .level(Level::Info)
        .build_with_sink(BoundedSink::new(ConsoleSink, 16));
    logger.log(LogEntry::new(Level::Info, "ready")).await?;
    logger.flush().await
}
