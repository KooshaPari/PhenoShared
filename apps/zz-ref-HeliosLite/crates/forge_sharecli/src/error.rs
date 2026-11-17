//! Typed error for ShareCLI operations.

use thiserror::Error;

/// Errors produced by ShareCLI channels, queues, and hub.
#[derive(Debug, Clone, Error, PartialEq, Eq)]
pub enum ShareError {
    /// Channel or queue has been closed.
    #[error("channel closed")]
    Closed,

    /// Bounded queue is full and cannot accept another message without blocking.
    #[error("channel full (capacity {capacity})")]
    Full {
        /// Capacity of the queue that rejected the push.
        capacity: usize,
    },

    /// Broadcast receiver lagged behind the sender and dropped messages.
    #[error("lagged {skipped} messages")]
    Lagged {
        /// Number of messages skipped.
        skipped: u64,
    },

    /// Topic name is invalid (empty or contains NUL).
    #[error("invalid topic: {reason}")]
    InvalidTopic {
        /// Human-readable reason.
        reason: String,
    },

    /// Generic transport / internal error.
    #[error("{0}")]
    Internal(String),
}
