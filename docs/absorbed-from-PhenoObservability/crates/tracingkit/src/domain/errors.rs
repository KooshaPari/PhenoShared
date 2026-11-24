//! Domain Errors

pub use phenotype_errors::DomainError as TraceError;

pub type TraceResult<T> = Result<T, TraceError>;
