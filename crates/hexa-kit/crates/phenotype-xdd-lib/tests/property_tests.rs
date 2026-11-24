//! Property-based tests using proptest.
//!
//! ## xDD Methodology: TDD + Property-Based Testing
//!
//! These tests verify properties of the library functions
//! using randomized inputs via proptest.

use phenotype_xdd_lib::property::strategies::*;
use proptest::{prop_assert, proptest};

proptest! {
    #[test]
    fn test_valid_uuid_property(s in "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}") {
        prop_assert!(valid_uuid(&s).is_ok());
    }

    #[test]
    fn test_bounded_int_always_in_range(n in -1000i64..=1000i64) {
        let result = bounded_int(n, -100, 100);
        if (-100..=100).contains(&n) {
            prop_assert!(result.is_ok());
        } else {
            prop_assert!(result.is_err());
        }
    }

    #[test]
    fn test_positive_int_never_zero_or_negative(n in -1000i64..=1000i64) {
        let result = positive_int(n);
        if n > 0 {
            prop_assert!(result.is_ok());
        } else {
            prop_assert!(result.is_err());
        }
    }

    #[test]
    fn test_non_empty_slice_never_empty(v in proptest::collection::vec(1i32..=1000, 0..=100)) {
        if v.is_empty() {
            prop_assert!(non_empty(&v).is_err());
        } else {
            prop_assert!(non_empty(&v).is_ok());
        }
    }
}
