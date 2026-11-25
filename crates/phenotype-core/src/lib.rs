//! # Phenotype Core
//!
//! Umbrella crate re-exporting all common phenotype crates for easier dependency management.
//!
//! ## Usage
//!
//! Instead of adding 10+ individual phenotype crates, add just this one:
//!
//! ```toml
//! [dependencies]
//! phenotype-core = { workspace = true }
//! ```
//!
//! ## Re-exports
//!
//! All major phenotype crates are re-exported:
//!
//! ```rust
//! // Error handling
//! use phenotype_core::error::{ApiError, DomainError, RepositoryError};
//!
//! // Configuration
//! use phenotype_core::config::{ConfigLoader, Priority};
//!
//! // Event bus
//! use phenotype_core::event_bus::{EventBus, EventEnvelope, EventId};
//!
//! // Validation
//! use phenotype_core::validation::{ValidationRule, RequiredRule};
//!
//! // Health
//! use phenotype_core::health::{HealthStatus, HealthChecker};
//!
//! // Telemetry
//! use phenotype_core::telemetry::{MetricsRecorder, SpanContext};
//!
//! // Ports
//! use phenotype_core::ports::{Repository, CachePort};
//!
//! // Contracts
//! use phenotype_core::contracts::{InMemoryRepository, InMemoryCache};
//!
//! // Retry
//! use phenotype_core::retry::{RetryPolicy, ExponentialBackoff};
//!
//! // Async
//! use phenotype_core::async_traits::AsyncIterator;
//!
//! // State machine
//! use phenotype_core::state_machine::{StateMachine, StateMachineBuilder};
//!
//! // Policy engine
//! use phenotype_core::policy::{PolicyEngine, PolicyResult};
//!
//! // Cache
//! use phenotype_core::cache::TwoTierCache;
//!
//! // String
//! use phenotype_core::string::StringExt;
//!
//! // Time
//! use phenotype_core::time::{DurationExt, Timestamp};
//!
//! // HTTP client
//! use phenotype_core::http::{HttpClient, RequestBuilder};
//! ```

#![doc = include_str!("../README.md")]

/// Error handling re-exports
pub mod error {
    pub use phenotype_error_core::{
        ApiError, ConfigError, DomainError, ErrorEnvelope, RepositoryError, StorageError,
    };
}

/// Configuration re-exports
pub mod config {
    pub use phenotype_config_core::{ConfigLoader, ConfigSource, Priority};
}

/// Event bus re-exports
pub mod event_bus {
    pub use phenotype_event_bus::{EventBus, EventBusError, EventEnvelope, EventId, Subscription};
}

/// Validation re-exports
pub mod validation {
    pub use phenotype_validation::{LengthRule, RequiredRule, ValidationError, ValidationRule};
}

/// Health re-exports
pub mod health {
    pub use phenotype_health::{
        CacheHealthChecker, DatabaseHealthChecker, ExternalServiceHealthChecker, HealthChecker,
        HealthMonitor, HealthResponse, HealthStatus, MemoryHealthChecker,
    };
}

/// Telemetry re-exports
pub mod telemetry {
    pub use phenotype_telemetry::{MetricsRecorder, SpanContext, TelemetryConfig};
}

/// Port traits re-exports
pub mod ports {
    pub use phenotype_port_traits::outbound::{CachePort, Repository, SecretPort};
}

/// Contracts re-exports
pub mod contracts {
    pub use phenotype_contracts::{
        InMemoryCache, InMemoryEventBus, InMemoryRepository, InMemorySecretManager,
    };
}

/// Retry re-exports
pub mod retry {
    pub use phenotype_retry::{RetryError, RetryPolicy};
}

/// Async traits re-exports
pub mod async_traits {
    pub use phenotype_async_traits::{
        AsyncDrop, AsyncDropper, AsyncFuture, AsyncIterator, BoxStream,
    };
}

/// State machine re-exports
pub mod state_machine {
    pub use phenotype_state_machine::{StateMachine, StateMachineBuilder, StateMachineError};
}

/// Policy engine re-exports
pub mod policy {
    pub use phenotype_policy_engine::{PolicyEngine, PolicyResult, RuleSet};
}

/// Cache re-exports
pub mod cache {
    pub use phenotype_cache_adapter::TwoTierCache;
}

/// String utilities re-exports
pub mod string {
    pub use phenotype_string::StringExt;
}

/// Time utilities re-exports
pub mod time {
    pub use phenotype_time::{DurationExt, Timestamp};
}

/// HTTP client re-exports
pub mod http {
    pub use phenotype_http_client_core::{HttpClient, RequestBuilder, Response, ResponseError};
}

/// External crate re-exports for convenience
pub mod external {
    /// ULID for sortable IDs
    pub use ulid::Ulid;

    /// DashMap for concurrent collections
    pub use dashmap::DashMap;

    /// Serde for serialization
    pub use serde::{de::DeserializeOwned, Deserialize, Serialize};

    /// Thiserror for error derives
    pub use thiserror::Error;

    /// Async-trait for async trait methods
    pub use async_trait::async_trait;

    /// Tokio for async runtime
    pub use tokio;

    /// Tracing for logging
    pub use tracing;
}

/// Prelude module for wildcard imports
pub mod prelude {
    pub use super::error::{ApiError, DomainError, RepositoryError, StorageError};
    pub use super::event_bus::{EventBus, EventEnvelope, EventId};
    pub use super::health::{HealthChecker, HealthStatus};
    pub use super::ports::{CachePort, Repository};
}

/// Convenience type aliases
pub mod types {
    use serde::{de::DeserializeOwned, Serialize};
    use std::fmt::Debug;

    /// Type alias for common result with DomainError
    pub type DomainResult<T> = std::result::Result<T, super::error::DomainError>;

    /// Type alias for common result with ApiError
    pub type ApiResult<T> = std::result::Result<T, super::error::ApiError>;

    /// Type alias for common result with RepositoryError
    pub type RepositoryResult<T> = std::result::Result<T, super::error::RepositoryError>;

    /// Type alias for common result with StorageError
    pub type StorageResult<T> = std::result::Result<T, super::error::StorageError>;

    /// Marker trait for event types
    pub trait Event: Serialize + DeserializeOwned + Send + Sync + Debug + 'static {}

    impl<T> Event for T where T: Serialize + DeserializeOwned + Send + Sync + Debug + 'static {}
}

#[cfg(test)]
mod tests {
    use super::prelude::*;
    use super::types::*;

    #[test]
    fn fr_core_001_error_types_available() {
        let domain_err = DomainError::not_found("test");
        assert!(matches!(domain_err, DomainError::NotFound(_)));

        let api_err = ApiError::not_found("test");
        assert!(matches!(api_err, ApiError::NotFound(_)));
    }

    #[test]
    fn fr_core_002_result_types_available() {
        fn returns_result() -> DomainResult<String> {
            Ok("success".to_string())
        }

        fn returns_error() -> DomainResult<String> {
            Err(DomainError::not_found("test"))
        }

        assert!(returns_result().is_ok());
        assert!(returns_error().is_err());
    }

    #[test]
    fn fr_core_003_external_crates_available() {
        let id = external::Ulid::new();
        assert!(!id.to_string().is_empty());
    }
}
