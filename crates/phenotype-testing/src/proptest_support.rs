//! Proptest integration for property-based testing support.
//!
//! Provides strategies and helpers for generating test data.
//!
//! # FR Traceability
//! - FR-TEST-002: Property-based testing integration

use proptest::prelude::*;

/// Strategies for generating test data.
///
/// # FR Traceability
/// - FR-TEST-002-001: Test data strategies
pub mod strategies {
    use super::*;

    /// Generate valid entity IDs (UUID-like strings).
    ///
    /// # FR Traceability
    /// - FR-TEST-002-002: Entity ID strategy
    pub fn entity_id() -> impl Strategy<Value = String> {
        "[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}".prop_map(|s| s.to_string())
    }

    /// Generate valid entity names (alphanumeric with spaces).
    ///
    /// # FR Traceability
    /// - FR-TEST-002-003: Entity name strategy
    pub fn entity_name() -> impl Strategy<Value = String> {
        prop::collection::vec("[a-zA-Z0-9 ]{1,50}", 1..5).prop_map(|parts| parts.join(" "))
    }

    /// Generate metadata key-value pairs.
    ///
    /// # FR Traceability
    /// - FR-TEST-002-004: Metadata strategy
    pub fn metadata() -> impl Strategy<Value = Vec<(String, String)>> {
        prop::collection::vec(("[a-z_]{1,20}", "[a-zA-Z0-9_\\-]{1,50}"), 0..10)
    }

    /// Generate a valid email-like string.
    ///
    /// # FR Traceability
    /// - FR-TEST-002-005: Email strategy
    pub fn email() -> impl Strategy<Value = String> {
        ("[a-z]{5,15}", "[a-z]{5,10}", "(com|org|net|io)")
            .prop_map(|(user, domain, tld)| format!("{}@{}.{}", user, domain, tld))
    }
}

/// Property-based test helpers.
///
/// # FR Traceability
/// - FR-TEST-002-006: Property test helpers
pub mod helpers {
    use proptest::test_runner::{Config, TestRunner};

    /// Run a property test with default configuration.
    ///
    /// # FR Traceability
    /// - FR-TEST-002-007: Property test runner
    pub fn run_property_test<F>(test: F)
    where
        F: Fn(&mut TestRunner) -> Result<(), proptest::test_runner::TestCaseError>,
    {
        let config = Config::default();
        let mut runner = TestRunner::new(config);
        test(&mut runner).unwrap();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    // Traces to: FR-TEST-002-002
    proptest! {
        #[test]
        fn entity_id_format(id in strategies::entity_id()) {
            // UUID format: 8-4-4-4-12 hex digits with dashes
            assert_eq!(id.len(), 36);
            assert_eq!(id.chars().nth(8), Some('-'));
            assert_eq!(id.chars().nth(13), Some('-'));
            assert_eq!(id.chars().nth(18), Some('-'));
            assert_eq!(id.chars().nth(23), Some('-'));
        }
    }

    // Traces to: FR-TEST-002-003
    proptest! {
        #[test]
        fn entity_name_not_empty(name in strategies::entity_name()) {
            assert!(!name.is_empty());
            assert!(name.len() <= 250);
        }
    }

    // Traces to: FR-TEST-002-005
    proptest! {
        #[test]
        fn email_contains_at(email in strategies::email()) {
            assert!(email.contains('@'));
            assert!(email.contains('.'));
        }
    }
}
