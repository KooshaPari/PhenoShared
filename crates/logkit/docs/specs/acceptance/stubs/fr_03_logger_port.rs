//! PENDING acceptance stub for FR-3 (Logger port).
//! maps-to: src/domain/logger.rs::Logger
//! feature: docs/specs/acceptance/fr-03-logger-port.feature

#![allow(dead_code, unused_imports)]

// use async_trait::async_trait;
// use logkit::{Level, LogEntry, LogError, Logger};

#[cfg(test)]
mod fr_03_logger_port {
    // struct MockLogger { level: Level }
    //
    // #[async_trait]
    // impl Logger for MockLogger {
    //     async fn log(&self, _entry: LogEntry) -> Result<(), LogError> { Ok(()) }
    //     fn level(&self) -> Level { self.level }
    // }

    // #[tokio::test]
    // async fn mock_logger_implements_port() {
    //     todo!("FR-3.1/FR-3.2: mock log() and level()");
    // }

    // fn assert_send_sync<T: Send + Sync>() {}
    //
    // #[test]
    // fn logger_is_send_sync() {
    //     todo!("FR-3.3: assert_send_sync::<Arc<dyn Logger>>()");
    // }
}
