use thiserror::Error;

#[derive(Error, Debug)]
pub enum ValidationError {
    #[error("Schema error: {0}")]
    SchemaError(String),
    
    #[error("Document error: {0}")]
    DocumentError(String),
    
    #[error("Schema not found: {0}")]
    SchemaNotFound(String),
}
