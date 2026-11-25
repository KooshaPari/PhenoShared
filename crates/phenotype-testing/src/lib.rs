//! Testing utilities and mock implementations for Phenotype ecosystem.
//!
//! Provides test fixtures, builders, property-based testing support,
//! and mock implementations of hexagonal architecture ports.
//!
//! # FR Traceability
//! - FR-TEST-001: Test fixture support
//! - FR-TEST-002: Property-based testing integration
//! - FR-TEST-003: Mock port implementations
//! - FR-TEST-004: Assertion helpers with traceability

pub mod assertions;
pub mod fixtures;
pub mod mocks;
pub mod proptest_support;

pub use assertions::*;
pub use fixtures::*;
pub use mocks::*;
pub use proptest_support::*;

/// Prelude module for convenient imports in tests.
pub mod prelude {
    pub use super::assertions::*;
    pub use super::fixtures::*;
    pub use super::mocks::*;
}
