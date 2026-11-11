//! Error types returned by the [`crate::Pipeline`] and its filters.

use thiserror::Error;

/// Errors that can occur while running a [`crate::Pipeline`].
#[derive(Error, Debug)]
pub enum PipelineError {
    /// A filter failed to process its inputs. The wrapped string contains
    /// a human-readable description of the failure.
    #[error("filter error: {0}")]
    Filter(String),

    /// The pipeline was empty when an operation required at least one item.
    #[error("empty pipeline: no items to process")]
    EmptyPipeline,
}

/// Convenience alias for `std::result::Result<T, PipelineError>`.
pub type Result<T> = std::result::Result<T, PipelineError>;