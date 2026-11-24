//! Common integration test utilities — harness, fixtures, HTTP client helpers.

pub mod fixtures;
pub mod harness;

pub use fixtures::{seed_test_data, TestFixtures};
pub use harness::{HarnessError, TestHarness};
