//! Test assertion helpers with FR traceability comments.
//!
//! Provides specialized assertions for common testing patterns.
//!
//! # FR Traceability
//! - FR-TEST-004: Assertion helpers with traceability

use std::fmt::Debug;

/// Assert that a result is Ok, with custom message.
///
/// # FR Traceability
/// - FR-TEST-004-001: Ok result assertion
#[macro_export]
macro_rules! assert_ok {
    ($result:expr) => {
        assert!(
            $result.is_ok(),
            "Expected Ok, got Err: {:?}",
            $result.unwrap_err()
        );
    };
    ($result:expr, $msg:expr) => {
        assert!(
            $result.is_ok(),
            "{}: got Err: {:?}",
            $msg,
            $result.unwrap_err()
        );
    };
}

/// Assert that a result is Err, with optional error type check.
///
/// # FR Traceability
/// - FR-TEST-004-002: Err result assertion
#[macro_export]
macro_rules! assert_err {
    ($result:expr) => {
        assert!(
            $result.is_err(),
            "Expected Err, got Ok: {:?}",
            $result.unwrap()
        );
    };
    ($result:expr, $msg:expr) => {
        assert!($result.is_err(), "{}: got Ok: {:?}", $msg, $result.unwrap());
    };
}

/// Assert that a result contains a specific value.
///
/// # FR Traceability
/// - FR-TEST-004-003: Value containment assertion
#[macro_export]
macro_rules! assert_ok_eq {
    ($result:expr, $expected:expr) => {
        match $result {
            Ok(actual) => assert_eq!(actual, $expected, "Result value mismatch"),
            Err(e) => panic!("Expected Ok({:?}), got Err: {:?}", $expected, e),
        }
    };
}

/// Assert that a collection contains an element matching predicate.
///
/// # FR Traceability
/// - FR-TEST-004-004: Collection contains assertion
pub fn assert_contains<T: Debug>(collection: &[T], predicate: impl Fn(&T) -> bool, msg: &str) {
    assert!(
        collection.iter().any(predicate),
        "{}: Collection {:?} did not contain matching element",
        msg,
        collection
    );
}

/// Assert that a collection has exactly N elements.
///
/// # FR Traceability
/// - FR-TEST-004-005: Collection length assertion
pub fn assert_count<T: Debug>(collection: &[T], expected: usize, msg: &str) {
    assert_eq!(
        collection.len(),
        expected,
        "{}: Expected {} elements, got {} in {:?}",
        msg,
        expected,
        collection.len(),
        collection
    );
}

/// Assert that two collections contain the same elements (order-independent).
///
/// # FR Traceability
/// - FR-TEST-004-006: Collection equality assertion
pub fn assert_set_eq<T: Eq + Debug + Clone>(a: &[T], b: &[T], msg: &str) {
    let mut a_sorted: Vec<_> = a.to_vec();
    let mut b_sorted: Vec<_> = b.to_vec();
    a_sorted.sort_by(|x, y| format!("{:?}", x).cmp(&format!("{:?}", y)));
    b_sorted.sort_by(|x, y| format!("{:?}", x).cmp(&format!("{:?}", y)));
    assert_eq!(a_sorted, b_sorted, "{}: Sets not equal", msg);
}

/// Assert that a string contains a substring.
///
/// # FR Traceability
/// - FR-TEST-004-007: String containment assertion
pub fn assert_str_contains(haystack: &str, needle: &str, msg: &str) {
    assert!(
        haystack.contains(needle),
        "{}: '{}' does not contain '{}'",
        msg,
        haystack,
        needle
    );
}

/// Assert that an error message contains expected text.
///
/// # FR Traceability
/// - FR-TEST-004-008: Error message assertion
pub fn assert_err_contains<E: Debug>(result: &Result<(), E>, expected: &str, msg: &str) {
    match result {
        Ok(_) => panic!("{}: Expected error, got Ok", msg),
        Err(e) => {
            let err_str = format!("{:?}", e);
            assert!(
                err_str.contains(expected),
                "{}: Error '{}' does not contain '{}'",
                msg,
                err_str,
                expected
            );
        }
    }
}

/// Assertion extensions for test types.
///
/// # FR Traceability
/// - FR-TEST-004-009: Assertion extension trait
pub trait TestAssertions {
    /// Assert self is Ok.
    fn assert_ok(self);
    /// Assert self is Err.
    fn assert_err(self);
}

impl<T: Debug, E: Debug> TestAssertions for Result<T, E> {
    fn assert_ok(self) {
        assert!(
            self.is_ok(),
            "Expected Ok, got Err: {:?}",
            self.unwrap_err()
        );
    }

    fn assert_err(self) {
        assert!(self.is_err(), "Expected Err, got Ok: {:?}", self.unwrap());
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-TEST-004-001
    #[test]
    fn assert_ok_macro_success() {
        let result: Result<i32, ()> = Ok(42);
        assert_ok!(result);
    }

    // Traces to: FR-TEST-004-002
    #[test]
    fn assert_err_macro_success() {
        let result: Result<(), &str> = Err("error");
        assert_err!(result);
    }

    // Traces to: FR-TEST-004-003
    #[test]
    fn assert_ok_eq_macro_success() {
        let result: Result<i32, ()> = Ok(42);
        assert_ok_eq!(result, 42);
    }

    // Traces to: FR-TEST-004-004
    #[test]
    fn assert_contains_success() {
        let data = vec![1, 2, 3, 4, 5];
        assert_contains(&data, |x| *x == 3, "Should contain 3");
    }

    // Traces to: FR-TEST-004-005
    #[test]
    fn assert_count_success() {
        let data = vec!["a", "b", "c"];
        assert_count(&data, 3, "Should have 3 elements");
    }

    // Traces to: FR-TEST-004-006
    #[test]
    fn assert_set_eq_success() {
        let a = vec![1, 2, 3];
        let b = vec![3, 2, 1];
        assert_set_eq(&a, &b, "Sets should be equal");
    }

    // Traces to: FR-TEST-004-007
    #[test]
    fn assert_str_contains_success() {
        assert_str_contains("hello world", "world", "Should contain 'world'");
    }

    // Traces to: FR-TEST-004-008
    #[test]
    fn assert_err_contains_success() {
        let result: Result<(), &str> = Err("something went wrong");
        assert_err_contains(&result, "went wrong", "Error should contain 'went wrong'");
    }
}
