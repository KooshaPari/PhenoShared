//! BDD Testing Infrastructure
//!
//! Provides BDD testing utilities for use with cucumber-rs.

/// TestContext provides shared state for BDD tests
#[derive(Debug, Clone)]
pub struct TestContext {
    pub data: std::collections::HashMap<String, serde_json::Value>,
    pub errors: Vec<TestError>,
    pub events: Vec<DomainEvent>,
}

impl TestContext {
    /// Create a new empty test context
    pub fn new() -> Self {
        Self {
            data: std::collections::HashMap::new(),
            errors: Vec::new(),
            events: Vec::new(),
        }
    }

    /// Reset the context for a new scenario
    pub fn reset(&mut self) {
        self.data.clear();
        self.errors.clear();
        self.events.clear();
    }

    /// Get a value from the context
    pub fn get(&self, key: &str) -> Option<&serde_json::Value> {
        self.data.get(key)
    }

    /// Set a value in the context
    pub fn set(&mut self, key: impl Into<String>, value: impl Into<serde_json::Value>) {
        self.data.insert(key.into(), value.into());
    }
}

impl Default for TestContext {
    fn default() -> Self {
        Self::new()
    }
}

/// Represents a test error
#[derive(Debug, Clone)]
pub struct TestError {
    pub kind: ErrorKind,
    pub message: String,
}

impl TestError {
    pub fn new(kind: ErrorKind, message: impl Into<String>) -> Self {
        Self {
            kind,
            message: message.into(),
        }
    }
}

/// Error kinds for test errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorKind {
    Validation,
    Domain,
    Auth,
    NotFound,
    Conflict,
    Internal,
}

/// Represents a domain event captured during testing
#[derive(Debug, Clone)]
pub struct DomainEvent {
    pub event_type: String,
    pub payload: serde_json::Value,
    pub timestamp: std::time::SystemTime,
}

/// Helper to create a feature tag
pub fn feature_tag(id: &str) -> String {
    format!("@FR-{}", id)
}

/// Helper to create a test type tag
pub fn test_type_tag(test_type: &str) -> String {
    format!("@{}", test_type)
}
