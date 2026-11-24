// SPDX-License-Identifier: MIT OR Apache-2.0

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

/// A single tool definition as loaded from a manifest.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    #[serde(default)]
    pub parameters: HashMap<String, String>,
}

/// Canonical error type for tool-registry operations.
#[derive(Error, Debug, PartialEq)]
pub enum ToolError {
    #[error("I/O error: {0}")]
    Io(String),
    #[error("JSON parse error: {0}")]
    Parse(String),
    #[error("Tool already registered: {0}")]
    Duplicate(String),
    #[error("Tool not found: {0}")]
    NotFound(String),
}

impl From<std::io::Error> for ToolError {
    fn from(err: std::io::Error) -> Self {
        ToolError::Io(err.to_string())
    }
}

impl From<serde_json::Error> for ToolError {
    fn from(err: serde_json::Error) -> Self {
        ToolError::Parse(err.to_string())
    }
}
