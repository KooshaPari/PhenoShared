// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! Schema validation module for heliosHarness
//!
//! Provides types and validation for configuration schemas.
//!
//! # Example
//!
//! ```rust
//! use harness_schema::{Schema, Command};
//!
//! let schema = Schema {
//!     name: "my_schema".to_string(),
//!     commands: vec![Command {
//!         name: "test".to_string(),
//!         command: "echo test".to_string(),
//!     }],
//! };
//! assert!(schema.validate().is_ok());
//! ```

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tracing::{debug, instrument};

/// Errors that can be produced by schema validation.
///
/// Traces to: FR-HELIOS-SCHEMA-001
#[derive(Debug, Error)]
pub enum SchemaError {
    /// The schema name is empty.
    #[error("schema name required")]
    EmptyName,

    /// A command within the schema has an empty name.
    #[error("command at index {0} has empty name")]
    EmptyCommandName(usize),

    /// A command within the schema has an empty command string.
    #[error("command at index {0} has empty command string")]
    EmptyCommandString(usize),

    /// Underlying I/O failure (e.g. reading schema from disk).
    ///
    /// Traces to: FR-HELIOS-IO-011
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
}

/// Schema definition containing commands and metadata
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Schema {
    /// Name of the schema
    pub name: String,
    /// List of commands defined in the schema
    pub commands: Vec<Command>,
}

/// A single command within a schema
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Command {
    /// Name of the command
    pub name: String,
    /// Command string to execute
    pub command: String,
}

impl Schema {
    /// Validates the schema
    ///
    /// # Errors
    ///
    /// Returns [`SchemaError::EmptyName`] if the schema name is empty,
    /// [`SchemaError::EmptyCommandName`] if any command has an empty name,
    /// or [`SchemaError::EmptyCommandString`] if any command has an empty
    /// command string.
    ///
    /// Traces to: FR-HELIOS-SCHEMA-001
    #[instrument(skip(self), fields(name = %self.name, commands = self.commands.len()))]
    pub fn validate(&self) -> Result<(), SchemaError> {
        if self.name.is_empty() {
            debug!("rejecting schema: empty name");
            return Err(SchemaError::EmptyName);
        }
        for (idx, cmd) in self.commands.iter().enumerate() {
            if cmd.name.is_empty() {
                debug!(idx, "rejecting schema: empty command name");
                return Err(SchemaError::EmptyCommandName(idx));
            }
            if cmd.command.is_empty() {
                debug!(idx, "rejecting schema: empty command string");
                return Err(SchemaError::EmptyCommandString(idx));
            }
        }
        debug!("schema validated");
        Ok(())
    }

    /// Returns the number of commands in the schema
    pub fn command_count(&self) -> usize {
        self.commands.len()
    }

    /// Finds a command by name
    pub fn find_command(&self, name: &str) -> Option<&Command> {
        self.commands.iter().find(|c| c.name == name)
    }
}

impl Command {
    /// Creates a new command
    pub fn new(name: &str, command: &str) -> Self {
        Self { name: name.to_string(), command: command.to_string() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_schema_validation_valid() {
        let schema = Schema { name: "test".to_string(), commands: vec![] };
        assert!(schema.validate().is_ok());
    }

    #[test]
    fn test_schema_validation_empty_name() {
        let schema = Schema { name: "".to_string(), commands: vec![] };
        assert!(matches!(schema.validate(), Err(SchemaError::EmptyName)));
    }

    #[test]
    fn test_command_count() {
        let schema = Schema {
            name: "test".to_string(),
            commands: vec![Command::new("a", "b"), Command::new("c", "d")],
        };
        assert_eq!(schema.command_count(), 2);
    }

    #[test]
    fn test_find_command() {
        let schema =
            Schema { name: "test".to_string(), commands: vec![Command::new("test", "echo test")] };
        assert!(schema.find_command("test").is_some());
        assert!(schema.find_command("missing").is_none());
    }

    /// Traces to: FR-HELIOS-SCHEMA-001
    #[test]
    fn test_schema_validation_empty_command_name() {
        let schema = Schema { name: "x".to_string(), commands: vec![Command::new("", "echo")] };
        assert!(matches!(schema.validate(), Err(SchemaError::EmptyCommandName(0))));
    }

    /// Traces to: FR-HELIOS-SCHEMA-001
    #[test]
    fn test_schema_validation_empty_command_string() {
        let schema = Schema { name: "x".to_string(), commands: vec![Command::new("ok", "")] };
        assert!(matches!(schema.validate(), Err(SchemaError::EmptyCommandString(0))));
    }

    /// Traces to: FR-HELIOS-IO-011
    #[test]
    fn from_io_error_maps_to_io_variant() {
        let io_err = std::io::Error::other("schema read failed");
        let err: SchemaError = io_err.into();
        assert!(matches!(err, SchemaError::Io(_)));
    }
}
