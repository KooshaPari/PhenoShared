# status: pending
# maps-to: src/domain/logger.rs::Logger, src/adapters/sinks/mod.rs::Sink
@nfr-1
Feature: Async-first I/O contracts
  Logger and Sink ports use async methods suitable for tokio runtimes.

  Scenario: Logger::log is awaitable inside tokio
  # PENDING: #[tokio::test] calls logger.log(entry).await

  Scenario: Sink write and flush are awaitable inside tokio
  # PENDING: #[tokio::test] calls sink.write(&entry).await and flush().await
