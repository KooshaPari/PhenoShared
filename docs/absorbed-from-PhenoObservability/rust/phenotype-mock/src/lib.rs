//! Mock testing utilities for phenotype crates
//!
//! Provides a flexible mock framework for testing including:
//! - Mock trait implementations
//! - Call recording and verification
//! - Expectation-based testing
//!
//! # Example
//!
//! ```rust
//! use phenotype_mock::{mock_trait, MockContext};
//!
//! // Create a mock context
//! let ctx = MockContext::new();
//!
//! // Record calls
//! ctx.record_call("get", vec!["id-1".to_string()]);
//!
//! // Verify expectations
//! assert!(ctx.verify_called("get"));
//! ```

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Mock call record
#[derive(Debug, Clone, Default)]
pub struct CallRecord {
    /// Method name
    pub method: String,
    /// Arguments
    pub args: Vec<String>,
    /// Return value
    pub return_value: Option<String>,
    /// Call count
    pub count: usize,
}

impl CallRecord {
    /// Create a new call record
    pub fn new(method: impl Into<String>, args: Vec<String>) -> Self {
        Self {
            method: method.into(),
            args,
            return_value: None,
            count: 0,
        }
    }

    /// Set return value
    pub fn returns(mut self, value: impl Into<String>) -> Self {
        self.return_value = Some(value.into());
        self
    }

    /// Increment call count
    pub fn increment(&mut self) {
        self.count += 1;
    }
}

/// Matcher for argument validation
#[derive(Debug, Clone, Default)]
pub struct Matcher {
    /// Expected method name
    pub method: String,
    /// Expected arguments (None = any)
    pub expected_args: Option<Vec<String>>,
}

impl Matcher {
    /// Create new matcher
    pub fn new(method: impl Into<String>) -> Self {
        Self {
            method: method.into(),
            expected_args: None,
        }
    }

    /// Set expected arguments
    pub fn with_args(mut self, args: Vec<impl Into<String>>) -> Self {
        self.expected_args = Some(args.into_iter().map(|a| a.into()).collect());
        self
    }

    /// Check if arguments match
    pub fn matches_args(&self, args: &[String]) -> bool {
        match &self.expected_args {
            Some(expected) => expected == args,
            None => true,
        }
    }
}

/// Mock expectation
#[derive(Debug, Clone, Default)]
pub struct Expectation {
    /// Matcher for method and arguments
    pub matcher: Matcher,
    /// Return value when matched
    pub return_value: Option<String>,
    /// Expected number of calls (None = any)
    pub times: Option<usize>,
    /// Actual call count
    pub called_count: usize,
}

impl Expectation {
    /// Check if this expectation was satisfied
    /// Requires `test-expectations` feature.
    #[cfg(feature = "test-expectations")]
    fn is_satisfied(&self) -> bool {
        match self.times {
            Some(expected) => self.called_count == expected,
            None => true, // Any number of calls is acceptable
        }
    }
}

/// Thread-safe storage for mock state
pub struct MockContext {
    /// All recorded calls
    calls: Arc<Mutex<Vec<CallRecord>>>,
    /// Current expectations by method name
    expectations: Arc<Mutex<HashMap<String, Vec<Expectation>>>>,
}

impl Default for MockContext {
    fn default() -> Self {
        Self::new()
    }
}

impl MockContext {
    /// Create a new mock context
    pub fn new() -> Self {
        Self {
            calls: Arc::new(Mutex::new(Vec::new())),
            expectations: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Record a method call
    pub fn record_call(&self, method: impl Into<String>, args: Vec<String>) {
        let mut calls = self.calls.lock().unwrap();
        let method_str = method.into();

        // Check if this is a new call or incrementing an existing one
        if let Some(record) = calls.iter_mut().find(|r| r.method == method_str && r.args == args) {
            record.increment();
            return;
        }

        // New call - create record and set initial count to 1
        let mut record = CallRecord::new(method_str, args);
        record.increment(); // First call
        calls.push(record);
    }

    /// Verify a method was called
    pub fn verify_called(&self, method: impl AsRef<str>) -> bool {
        let calls = self.calls.lock().unwrap();
        calls.iter().any(|r| r.method == method.as_ref())
    }

    /// Verify a method was called with specific arguments
    pub fn verify_called_with(&self, method: impl AsRef<str>, args: &[&str]) -> bool {
        let calls = self.calls.lock().unwrap();
        let args_owned: Vec<String> = args.iter().map(|&a| a.into()).collect();
        calls.iter().any(|r| r.method == method.as_ref() && r.args == args_owned)
    }

    /// Verify exact call count
    pub fn verify_call_count(&self, method: impl AsRef<str>, expected: usize) -> bool {
        let calls = self.calls.lock().unwrap();
        let total: usize = calls
            .iter()
            .filter(|r| r.method == method.as_ref())
            .map(|r| r.count.max(1))
            .sum();
        total == expected
    }

    /// Get call count
    pub fn call_count(&self, method: impl AsRef<str>) -> usize {
        let calls = self.calls.lock().unwrap();
        calls
            .iter()
            .filter(|r| r.method == method.as_ref())
            .map(|r| r.count.max(1))
            .sum()
    }

    /// Create expectation builder
    pub fn expect(&self, method: impl Into<String>) -> ExpectationBuilder {
        ExpectationBuilder {
            expectations: self.expectations.clone(),
            method: method.into(),
            expected_args: None,
            return_value: None,
            times: None,
        }
    }

    /// Get return value for a method call
    pub fn get_return_value(&self, method: impl AsRef<str>, args: &[String]) -> Option<String> {
        let expectations = self.expectations.lock().unwrap();
        let method_expectations = expectations.get(method.as_ref())?;

        for exp in method_expectations {
            if exp.matcher.matches_args(args) {
                // Increment the expectation call count
                return exp.return_value.clone();
            }
        }
        None
    }

    /// Verify all expectations
    pub fn verify_all(&self) -> Result<(), Vec<String>> {
        let expectations = self.expectations.lock().unwrap();
        let mut failures = Vec::new();

        for (method, exps) in expectations.iter() {
            for exp in exps.iter() {
                match exp.times {
                    Some(expected) if exp.called_count != expected => {
                        failures.push(format!(
                            "Method '{}' expected {} calls, got {}",
                            method, expected, exp.called_count
                        ));
                    }
                    _ => {}
                }
            }
        }

        if failures.is_empty() {
            Ok(())
        } else {
            Err(failures)
        }
    }
}

/// Builder for constructing expectations
pub struct ExpectationBuilder {
    expectations: Arc<Mutex<HashMap<String, Vec<Expectation>>>>,
    method: String,
    expected_args: Option<Vec<String>>,
    return_value: Option<String>,
    times: Option<usize>,
}

impl ExpectationBuilder {
    /// Expect specific arguments
    pub fn with_args(mut self, args: Vec<impl Into<String>>) -> Self {
        self.expected_args = Some(args.into_iter().map(|a| a.into()).collect());
        self
    }

    /// Set return value
    pub fn returns<T: Into<String>>(mut self, value: T) -> Self {
        self.return_value = Some(value.into());
        self
    }

    /// Set expected call count
    pub fn times(mut self, count: usize) -> Self {
        self.times = Some(count);
        self
    }

    /// Build and add expectation
    pub fn build(self) {
        let matcher = Matcher {
            method: self.method.clone(),
            expected_args: self.expected_args,
        };
        
        let expectation = Expectation {
            matcher,
            return_value: self.return_value,
            times: self.times,
            called_count: 0,
        };

        let mut expectations = self.expectations.lock().unwrap();
        expectations
            .entry(self.method)
            .or_default()
            .push(expectation);
    }
}

/// Macro for creating mock implementations
#[macro_export]
macro_rules! mock_trait {
    (
        $name:ident for $trait:path {
            $(
                fn $method:ident($($arg:ident: $ty:ty),*) -> $ret:ty;
            )*
        }
    ) => {
        pub struct $name {
            context: phenotype_mock::MockContext,
        }

        impl $name {
            pub fn new() -> Self {
                Self {
                    context: phenotype_mock::MockContext::new(),
                }
            }

            pub fn context(&self) -> &phenotype_mock::MockContext {
                &self.context
            }
        }

        impl Default for $name {
            fn default() -> Self {
                Self::new()
            }
        }
    };
}

/// Mock return value helper
pub fn mock_return<T: Into<String>>(value: T) -> Option<String> {
    Some(value.into())
}

/// Verify helper
pub fn verify<T>(condition: bool, message: impl Into<String>) -> Result<(), String> {
    if condition {
        Ok(())
    } else {
        Err(message.into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mock_context_record_call() {
        let ctx = MockContext::new();

        ctx.record_call("get", vec!["id-1".to_string()]);
        ctx.record_call("get", vec!["id-1".to_string()]); // Same call again
        ctx.record_call("put", vec!["id-2".to_string(), "value".to_string()]);

        assert!(ctx.verify_called("get"));
        assert!(ctx.verify_called("put"));
        assert!(!ctx.verify_called("delete"));

        assert!(ctx.verify_call_count("get", 2));
        assert!(ctx.verify_called_with("put", &["id-2", "value"]));
    }

    #[test]
    fn test_expectation() {
        let ctx = MockContext::new();

        ctx.expect("get")
            .with_args(vec!["id-1"])
            .returns("value-1")
            .times(1)
            .build();

        let result: Option<String> = ctx.get_return_value("get", &["id-1".to_string()]);
        assert_eq!(result, Some("value-1".to_string()));

        let no_match: Option<String> = ctx.get_return_value("get", &["id-2".to_string()]);
        assert_eq!(no_match, None);
    }
}
