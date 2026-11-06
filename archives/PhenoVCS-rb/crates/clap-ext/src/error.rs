//! `CliError`: shared error enum for 60+ CLIs.

use thiserror::Error;

/// Unified CLI error type for clap-ext adopters.
///
/// Implements `From<std::io::Error>`, `From<anyhow::Error>`,
/// `From<&str>`, and `From<String>` so any error can be `?`-propagated
/// into a `CliResult<T>`.
#[derive(Debug, Error)]
pub enum CliError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Config error: {0}")]
    Config(String),

    #[error("Parse error: {0}")]
    Parse(String),

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Network error: {0}")]
    Network(String),

    #[error(transparent)]
    Other(#[from] anyhow::Error),
}

impl From<&str> for CliError {
    fn from(s: &str) -> Self {
        CliError::Other(anyhow::anyhow!(s.to_string()))
    }
}

impl From<String> for CliError {
    fn from(s: String) -> Self {
        CliError::Other(anyhow::anyhow!(s))
    }
}

/// Convenience: exit the process with a formatted error message and code 1.
pub fn exit_with<E: std::fmt::Display>(err: E) -> ! {
    eprintln!("error: {err}");
    std::process::exit(1);
}

/// Standard `Result` alias for CLIs.
pub type CliResult<T> = Result<T, CliError>;
