//! phenotype-test-infra - Testing Infrastructure for Phenotype Stack
//!
//! This crate provides testing utilities including:
//! - BDD testing infrastructure with cucumber integration
//! - Test fixtures and builders
//! - Assertion helpers
//! - Test utilities for async and sync code

pub mod assertions;
pub mod bdd;
pub mod fixtures;

// Re-export commonly used types
pub use assertions::Assertion;
pub use bdd::TestContext;
pub use fixtures::TempDirFixture;
