use std::collections::HashMap;

use async_trait::async_trait;
use aws_sdk_s3::presigning::PresigningConfig;
use aws_sdk_s3::primitives::ByteStream;
use aws_sdk_s3::Client;

use crate::ports::{TransportError, UploadReceipt, UploadRequest, UploadTransport};

#[derive(Debug, Clone)]
pub struct S3UploadTransport {
    client: Client,
    upload_bucket: String,
    abort_bucket: String,
}

impl S3UploadTransport {
    pub fn new(client: Client, bucket: impl Into<String>) -> Self {
        let bucket = bucket.into();
        Self {
            client,
            upload_bucket: bucket.clone(),
            abort_bucket: bucket,
        }
    }

    pub fn with_abort_bucket(
        client: Client,
        upload_bucket: impl Into<String>,
        abort_bucket: impl Into<String>,
    ) -> Self {
        Self {
            client,
            upload_bucket: upload_bucket.into(),
            abort_bucket: abort_bucket.into(),
        }
    }

    pub async fn presign_upload(
        &self,
        req: &UploadRequest,
    ) -> Result<UploadReceipt, TransportError> {
        validate_upload_request(req)?;

        let mut operation = self
            .client
            .put_object()
            .bucket(resolve_bucket(&self.upload_bucket, &req.bucket)?)
            .key(&req.object_key)
            .content_type(&req.content_type);

        if let Some(content_length) = req.content_length {
            operation = operation.content_length(content_length);
        }

        if let Some(checksum_sha256) = &req.checksum_sha256 {
            operation = operation.checksum_sha256(checksum_sha256);
        }

        let presigned = operation
            .body(ByteStream::from_static(b""))
            .presigned(presign_config(req.expires_in)?)
            .await
            .map_err(|error| TransportError::Presign(error.to_string()))?;

        let method = presigned.method().to_string();
        let url = presigned.uri().to_string().parse()?;
        let headers = presigned
            .headers()
            .map(|(name, value)| (name.to_owned(), value.to_owned()))
            .collect::<HashMap<_, _>>();

        Ok(UploadReceipt {
            id: req.id.clone(),
            method,
            url,
            headers,
        })
    }
}

#[async_trait]
impl UploadTransport for S3UploadTransport {
    async fn upload(&self, req: UploadRequest) -> Result<UploadReceipt, TransportError> {
        self.presign_upload(&req).await
    }

    async fn abort(&self, id: &str) -> Result<(), TransportError> {
        if id.trim().is_empty() {
            return Err(TransportError::InvalidRequest("upload id cannot be empty"));
        }

        self.client
            .delete_object()
            .bucket(resolve_bucket(&self.abort_bucket, "")?)
            .key(id)
            .send()
            .await
            .map_err(|error| TransportError::S3(error.to_string()))?;

        Ok(())
    }
}

fn resolve_bucket(configured_bucket: &str, request_bucket: &str) -> Result<String, TransportError> {
    if !request_bucket.trim().is_empty() {
        return Ok(request_bucket.to_owned());
    }

    if configured_bucket.trim().is_empty() {
        return Err(TransportError::MissingConfiguration("s3 bucket"));
    }

    Ok(configured_bucket.to_owned())
}

fn validate_upload_request(req: &UploadRequest) -> Result<(), TransportError> {
    if req.id.trim().is_empty() {
        return Err(TransportError::InvalidRequest("upload id cannot be empty"));
    }
    if req.object_key.trim().is_empty() {
        return Err(TransportError::InvalidRequest("object key cannot be empty"));
    }
    if req.content_type.trim().is_empty() {
        return Err(TransportError::InvalidRequest(
            "content type cannot be empty",
        ));
    }

    Ok(())
}

fn presign_config(expires_in: std::time::Duration) -> Result<PresigningConfig, TransportError> {
    PresigningConfig::expires_in(expires_in).map_err(|error| {
        TransportError::InvalidRequest(Box::leak(error.to_string().into_boxed_str()))
    })
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use aws_sdk_s3::config::{Credentials, Region};

    use super::*;

    #[tokio::test]
    async fn presign_upload_generates_put_receipt() {
        let transport = transport_for_tests().await;
        let req = UploadRequest {
            id: "upload-123".into(),
            bucket: String::new(),
            object_key: "artifacts/report.txt".into(),
            content_type: "text/plain".into(),
            content_length: Some(32),
            checksum_sha256: None,
            expires_in: Duration::from_secs(300),
        };

        let receipt = transport
            .presign_upload(&req)
            .await
            .expect("presign should succeed");

        assert_eq!(receipt.id, "upload-123");
        assert_eq!(receipt.method, "PUT");
        assert_eq!(receipt.url.scheme(), "https");
        assert!(receipt.url.as_str().contains("artifacts/report.txt"));
        assert!(receipt
            .url
            .query()
            .expect("signed query")
            .contains("X-Amz-Signature"));
    }

    #[tokio::test]
    async fn presign_upload_uses_request_bucket_override() {
        let transport = transport_for_tests().await;
        let req = UploadRequest {
            id: "upload-456".into(),
            bucket: "alternate-bucket".into(),
            object_key: "nested/image.png".into(),
            content_type: "image/png".into(),
            content_length: None,
            checksum_sha256: Some("deadbeef".into()),
            expires_in: Duration::from_secs(60),
        };

        let receipt = transport
            .presign_upload(&req)
            .await
            .expect("presign should succeed");

        assert_eq!(receipt.method, "PUT");
        assert!(receipt
            .url
            .host_str()
            .expect("host")
            .starts_with("alternate-bucket."));
        assert!(receipt.url.path().ends_with("/nested/image.png"));
    }

    async fn transport_for_tests() -> S3UploadTransport {
        let config = aws_sdk_s3::config::Builder::new()
            .region(Region::new("us-east-1"))
            .credentials_provider(Credentials::new(
                "test-access-key",
                "test-secret-key",
                None,
                None,
                "unit-test",
            ))
            .build();

        let client = Client::from_conf(config);
        S3UploadTransport::new(client, "byteport-test-bucket")
    }
}
