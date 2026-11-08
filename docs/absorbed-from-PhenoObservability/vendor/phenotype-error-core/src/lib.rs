//! Canonical error types for the Phenotype ecosystem.
//!
//! This crate provides a unified error framework for transport, domain,
//! persistence, configuration, and storage layers. It also exposes the shared
//! wire error contract used by TypeScript package `@phenotype/errors`.

mod code;
mod context;
mod envelope;
mod layered;

pub use code::{ErrorCode, ERROR_CODES};
pub use context::ErrorContext;
pub use envelope::ErrorEnvelope;
pub use layered::{ApiError, ConfigError, DomainError, RepositoryError, StorageError};
