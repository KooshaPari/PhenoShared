use std::collections::HashMap;
use std::time::Duration;

use async_trait::async_trait;
use thiserror::Error;
use url::Url;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UploadRequest {
    pub id: String,
    pub bucket: String,
    pub object_key: String,
    pub content_type: String,
    pub content_length: Option<i64>,
    pub checksum_sha256: Option<String>,
    pub expires_in: Duration,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UploadReceipt {
    pub id: String,
    pub method: String,
    pub url: Url,
    pub headers: HashMap<String, String>,
}

#[derive(Debug, Error)]
pub enum TransportError {
    #[error("missing transport configuration: {0}")]
    MissingConfiguration(&'static str),
    #[error("invalid upload request: {0}")]
    InvalidRequest(&'static str),
    #[error("s3 presign failed: {0}")]
    Presign(String),
    #[error("s3 operation failed: {0}")]
    S3(String),
    #[error("invalid signed url: {0}")]
    Url(#[from] url::ParseError),
}

#[async_trait]
pub trait UploadTransport: Send + Sync {
    async fn upload(&self, req: UploadRequest) -> Result<UploadReceipt, TransportError>;
    async fn abort(&self, id: &str) -> Result<(), TransportError>;
}
