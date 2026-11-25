use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum DiffError {
    #[error("patch applies to wrong source: expected context '{expected}', got '{got}'")]
    ContextMismatch { expected: String, got: String },

    #[error("patch hunk is out of range (line {line} not in source of {source_len} lines)")]
    OutOfRange { line: usize, source_len: usize },

    #[error("patch is malformed: {0}")]
    Malformed(String),
}
