//! Structured CLI error types with user-facing hints and machine-readable output.
//!
//! Traceability: L14 remediation — wraps raw `anyhow` errors in a typed envelope
//! that provides a recovery hint and optional JSON serialization.

use std::fmt;
use std::process;

use serde::Serialize;

/// Output mode for error rendering.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputMode {
    /// Human-readable terminal output (default).
    Text,
    /// Machine-readable JSON output.
    Json,
}

impl OutputMode {
    /// Resolve the output mode from the `AGILEPLUS_OUTPUT` env var.
    pub fn from_env() -> Self {
        match std::env::var("AGILEPLUS_OUTPUT").as_deref() {
            Ok("json") => OutputMode::Json,
            _ => OutputMode::Text,
        }
    }
}

/// A structured CLI error with category, message, and recovery hint.
///
/// # Traceability: FR-088 / WP15-T065
#[derive(Debug, Serialize)]
pub struct CliError {
    /// Error category — maps to a generic classification.
    pub category: ErrorCategory,
    /// User-facing description (safe to show to end users).
    pub message: String,
    /// Optional hint about how to fix the problem.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hint: Option<String>,
    /// Exit code to use when this error terminates the process.
    #[serde(skip)]
    pub exit_code: i32,
}

/// High-level error categories for the CLI.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum ErrorCategory {
    /// Configuration / env-var / file-not-found errors.
    Config,
    /// I/O errors (disk, network).
    Io,
    /// Git/VCS operation failures.
    Git,
    /// Input validation failures.
    Validation,
    /// Internal / unexpected errors.
    Internal,
}

impl fmt::Display for ErrorCategory {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ErrorCategory::Config => write!(f, "CONFIG"),
            ErrorCategory::Io => write!(f, "IO"),
            ErrorCategory::Git => write!(f, "GIT"),
            ErrorCategory::Validation => write!(f, "VALIDATION"),
            ErrorCategory::Internal => write!(f, "INTERNAL"),
        }
    }
}

impl CliError {
    /// Create a new `CliError` with the given category, message, and optional hint.
    pub fn new(category: ErrorCategory, message: impl Into<String>) -> Self {
        Self {
            category,
            message: message.into(),
            hint: None,
            exit_code: 1,
        }
    }

    /// Attach a recovery hint.
    pub fn with_hint(mut self, hint: impl Into<String>) -> Self {
        self.hint = Some(hint.into());
        self
    }

    /// Set an explicit exit code.
    pub fn with_exit_code(mut self, code: i32) -> Self {
        self.exit_code = code;
        self
    }

    /// Classify an `anyhow::Error` into a structured `CliError`.
    ///
    /// Heuristic classification based on error content:
    /// - `git` / `fatal:` → `Git`
    /// - `No such file` / `denied` / `Permission` → `Io`
    /// - `found` / `expected` / `invalid` → `Validation`
    /// - everything else → `Internal`
    pub fn from_anyhow(err: &anyhow::Error) -> Self {
        let msg = format!("{err:#}");
        let display = format!("{err}");

        let category = if msg.contains("fatal:")
            || msg.contains("git")
            || msg.contains("Not inside a git repository")
        {
            ErrorCategory::Git
        } else if msg.contains("No such file")
            || msg.contains("Permission denied")
            || msg.contains("denied")
            || msg.contains("creating directory")
            || msg.contains("opening database")
        {
            ErrorCategory::Io
        } else if msg.contains("found")
            || msg.contains("expected")
            || msg.contains("invalid")
        {
            ErrorCategory::Validation
        } else {
            ErrorCategory::Internal
        };

        let hint = match category {
            ErrorCategory::Git => {
                Some("Ensure you are inside a git repository and the remote is accessible. Run `git status` to verify.".into())
            }
            ErrorCategory::Io => {
                Some("Check that the path exists and you have the necessary permissions.".into())
            }
            ErrorCategory::Config => {
                Some("Check your configuration file and environment variables.".into())
            }
            ErrorCategory::Validation => {
                Some("Review the command arguments and try again with valid input.".into())
            }
            ErrorCategory::Internal => {
                Some("This is an unexpected error. Please report it with the full output of `agileplus -vvv <command>`.".into())
            }
        };

        Self {
            category,
            message: display,
            hint: Some(hint),
            exit_code: 1,
        }
    }

    /// Render the error to stderr according to the output mode, then exit.
    pub fn exit(self, mode: OutputMode) -> ! {
        match mode {
            OutputMode::Json => {
                let json = serde_json::to_string_pretty(&self)
                    .unwrap_or_else(|_| r#"{"category":"INTERNAL","message":"serialization failed"}"#.to_string());
                eprintln!("{json}");
            }
            OutputMode::Text => {
                eprintln!("Error [{}]: {}", self.category, self.message);
                if let Some(hint) = &self.hint {
                    eprintln!("Hint: {hint}");
                }
            }
        }
        process::exit(self.exit_code);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn classify_git_error() {
        let e = anyhow::anyhow!("fatal: not a git repository");
        let ce = CliError::from_anyhow(&e);
        assert_eq!(ce.category, ErrorCategory::Git);
        assert!(ce.hint.unwrap().contains("git repository"));
    }

    #[test]
    fn classify_io_error() {
        let e = anyhow::anyhow!("No such file or directory: /tmp/foo");
        let ce = CliError::from_anyhow(&e);
        assert_eq!(ce.category, ErrorCategory::Io);
    }

    #[test]
    fn classify_internal_error() {
        let e = anyhow::anyhow!("something unexpected happened");
        let ce = CliError::from_anyhow(&e);
        assert_eq!(ce.category, ErrorCategory::Internal);
    }

    #[test]
    fn json_output_serializes() {
        let err = CliError::new(ErrorCategory::Config, "missing env var")
            .with_hint("Set AGILEPLUS_CREDENTIAL_PASSPHRASE");
        let json = serde_json::to_string(&err).unwrap();
        assert!(json.contains("CONFIG"));
        assert!(json.contains("missing env var"));
        assert!(json.contains("AGILEPLUS_CREDENTIAL_PASSPHRASE"));
    }

    #[test]
    fn output_mode_from_env() {
        unsafe { std::env::set_var("AGILEPLUS_OUTPUT", "json") };
        assert_eq!(OutputMode::from_env(), OutputMode::Json);
        unsafe { std::env::remove_var("AGILEPLUS_OUTPUT") };
        assert_eq!(OutputMode::from_env(), OutputMode::Text);
    }
}
