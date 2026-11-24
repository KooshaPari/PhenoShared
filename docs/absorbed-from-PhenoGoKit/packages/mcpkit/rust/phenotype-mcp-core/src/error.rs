//! MCP Error types

use std::fmt;

/// MCP error
#[derive(Debug, Clone)]
pub struct McpError {
    pub code: ErrorCode,
    pub message: String,
}

/// MCP error codes
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ErrorCode {
    ParseError = -32700,
    InvalidRequest = -32600,
    MethodNotFound = -32601,
    InvalidParams = -32602,
    InternalError = -32603,
}

impl fmt::Display for McpError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "MCP Error ({}): {}", self.code as i32, self.message)
    }
}

impl std::error::Error for McpError {}

impl McpError {
    pub fn new(code: ErrorCode, message: impl Into<String>) -> Self {
        Self {
            code,
            message: message.into(),
        }
    }

    /// Get the error code
    pub fn code(&self) -> ErrorCode {
        self.code
    }

    /// Get the error message
    pub fn message(&self) -> &str {
        &self.message
    }
}

/// Result type for MCP operations
pub type Result<T> = std::result::Result<T, McpError>;

/// Aliased result type for convenience
pub type McpResult<T> = Result<T>;
