// SPDX-License-Identifier: MIT OR Apache-2.0
//! Domain layer - pure configuration logic.

pub mod config;
pub mod errors;
pub mod idempotency;
pub mod layers;
pub mod ports;
pub mod sources;
pub mod validation;

// Re-exports
pub use config::{Config, ConfigPath, ConfigValue};
pub use errors::ConfigError;
pub use idempotency::{
    DeadLetterEntry, DeadLetterQueue, IdempotencyKey, IdempotencyStore, SubmissionResult,
};
pub use layers::{Layer, LayerPriority, LayerStack, MergeStrategy};
pub use sources::Source;
pub use validation::Validator;
