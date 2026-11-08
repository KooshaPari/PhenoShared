// SPDX-License-Identifier: MIT OR Apache-2.0
//! Configuration management framework.
//!
//! # Architecture
//!
//! settly follows hexagonal architecture:
//!
//! - **Domain**: Pure business logic (config entities, layers, validation)
//! - **Application**: Use cases and configuration builder
//! - **Adapters**: File parsers, env sources, validators
//! - **Infrastructure**: Cross-cutting concerns (error handling, logging)
//!
//! # Quick Start
//!
//! ```
//! use settly::ConfigBuilder;
//!
//! let config = ConfigBuilder::new().build().unwrap();
//! ```

pub mod adapters;
pub mod application;
pub mod config;
pub mod domain;
pub mod infrastructure;

// Re-exports
pub use adapters::idempotency::{InMemoryDlq, InMemoryIdempotencyStore};
pub use application::builder::ConfigBuilder;
pub use application::submission::SubmissionService;
pub use domain::errors::ConfigError;
pub use domain::{Config, ConfigValue, Layer, LayerPriority};
pub use domain::{
    DeadLetterEntry, DeadLetterQueue, IdempotencyKey, IdempotencyStore, SubmissionResult,
};
pub use infrastructure::error::ConfigKitError;

/// Framework version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
