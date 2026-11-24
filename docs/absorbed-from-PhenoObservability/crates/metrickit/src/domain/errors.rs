//! Domain Errors

use thiserror::Error;

#[derive(Debug, Error)]
pub enum MetricError {
    #[error("Metric already registered: {0}")]
    AlreadyRegistered(String),

    #[error("Metric not found: {0}")]
    NotFound(String),

    #[error("Export error: {0}")]
    Export(String),
}

pub type MetricResult<T> = Result<T, MetricError>;
