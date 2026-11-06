//! Domain errors.

#[derive(Debug, thiserror::Error)]
pub enum CacheError {
    #[error("Key not found: {0}")]
    KeyNotFound(String),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("Deserialization error: {0}")]
    DeserializationError(String),

    #[error("Cache full")]
    CacheFull,

    #[error("Backend error: {0}")]
    BackendError(String),

    #[error("IO error: {0}")]
    IoError(String),
}

impl serde::Serialize for CacheError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        serializer.serialize_str(&self.to_string())
    }
}
