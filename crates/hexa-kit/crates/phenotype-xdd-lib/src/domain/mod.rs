//! Domain layer - Pure business logic with no external dependencies.
//!
//! ## Error Handling (PoLA - Principle of Least Astonishment)
//!
//! All domain errors follow these principles:
//! 1. Messages are descriptive and actionable
//! 2. Context is attached for debugging
//! 3. Errors are categorized by domain concept

use std::fmt;

use serde::{Deserialize, Serialize};

/// Domain-level result type for consistent error handling.
pub type XddResult<T> = Result<T, XddError>;

/// Base error type for xDD operations.
///
/// Follows PoLA: error messages are descriptive, actionable,
/// and include context for debugging.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XddError {
    /// Human-readable error message
    pub message: String,
    /// Error category for programmatic handling
    pub category: ErrorCategory,
    /// Additional context for debugging
    #[serde(default)]
    pub context: serde_json::Value,
}

impl XddError {
    /// Create a new XddError with message and category.
    pub fn new(message: impl Into<String>, category: ErrorCategory) -> Self {
        Self {
            message: message.into(),
            category,
            context: serde_json::Value::Null,
        }
    }

    /// Add context to an error.
    pub fn with_context(mut self, key: impl Into<String>, value: impl Serialize) -> Self {
        let key_str = key.into();
        let value_json = serde_json::json!(value);
        if let Some(map) = self.context.as_object_mut() {
            map.insert(key_str, value_json);
        } else {
            let mut map = serde_json::Map::new();
            map.insert(key_str, value_json);
            self.context = serde_json::Value::Object(map);
        }
        self
    }

    /// Create a property testing error.
    pub fn property(message: impl Into<String>) -> Self {
        Self::new(message, ErrorCategory::Property)
    }

    /// Create a contract verification error.
    pub fn contract(message: impl Into<String>) -> Self {
        Self::new(message, ErrorCategory::Contract)
    }

    /// Create a mutation coverage error.
    pub fn mutation(message: impl Into<String>) -> Self {
        Self::new(message, ErrorCategory::Mutation)
    }

    /// Create a specification parsing error.
    pub fn spec(message: impl Into<String>) -> Self {
        Self::new(message, ErrorCategory::Spec)
    }
}

impl fmt::Display for XddError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[{:?}] {}", self.category, self.message)
    }
}

impl std::error::Error for XddError {}

/// Error categories for programmatic handling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ErrorCategory {
    /// Property-based testing errors
    Property,
    /// Contract testing errors
    Contract,
    /// Mutation testing errors
    Mutation,
    /// Specification parsing/validation errors
    Spec,
    /// Internal/unexpected errors
    Internal,
}

impl fmt::Display for ErrorCategory {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ErrorCategory::Property => write!(f, "property"),
            ErrorCategory::Contract => write!(f, "contract"),
            ErrorCategory::Mutation => write!(f, "mutation"),
            ErrorCategory::Spec => write!(f, "spec"),
            ErrorCategory::Internal => write!(f, "internal"),
        }
    }
}
