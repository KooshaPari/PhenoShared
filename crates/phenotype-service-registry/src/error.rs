use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum RegistryError {
    #[error("service not found: {0}")]
    NotFound(String),

    #[error("service already registered: {id}")]
    AlreadyRegistered { id: String },

    #[error("internal registry error: {0}")]
    Internal(String),
}
