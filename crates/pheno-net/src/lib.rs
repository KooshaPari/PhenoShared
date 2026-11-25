//! PhenoNet - Network Utilities

use anyhow::Result;
use reqwest::{Client, StatusCode};
use std::time::Duration;
use thiserror::Error;
use tokio::sync::Semaphore;

#[derive(Error, Debug)]
pub enum NetError {
    #[error("request failed: {0}")]
    RequestFailed(String),
    #[error("rate limited")]
    RateLimited,
    #[error("timeout")]
    Timeout,
    #[error("invalid URL: {0}")]
    InvalidUrl(String),
}

/// HTTP client with rate limiting
pub struct HttpClient {
    client: Client,
    rate_limiter: Semaphore,
}

impl HttpClient {
    pub fn new() -> Result<Self> {
        let client = Client::builder()
            .pool_max_idle_per_host(10)
            .timeout(Duration::from_secs(30))
            .build()?;

        Ok(Self {
            client,
            rate_limiter: Semaphore::new(100),
        })
    }

    pub async fn get(&self, url: &str) -> Result<String, NetError> {
        let _permit = self
            .rate_limiter
            .acquire()
            .await
            .map_err(|_| NetError::RateLimited)?;

        let response = self
            .client
            .get(url)
            .send()
            .await
            .map_err(|e| NetError::RequestFailed(e.to_string()))?;

        self.handle_response(response).await
    }

    pub async fn post(&self, url: &str, body: serde_json::Value) -> Result<String, NetError> {
        let _permit = self
            .rate_limiter
            .acquire()
            .await
            .map_err(|_| NetError::RateLimited)?;

        let response = self
            .client
            .post(url)
            .json(&body)
            .send()
            .await
            .map_err(|e| NetError::RequestFailed(e.to_string()))?;

        self.handle_response(response).await
    }

    async fn handle_response(&self, response: reqwest::Response) -> Result<String, NetError> {
        match response.status() {
            StatusCode::OK => response
                .text()
                .await
                .map_err(|e| NetError::RequestFailed(e.to_string())),
            StatusCode::TOO_MANY_REQUESTS => Err(NetError::RateLimited),
            StatusCode::REQUEST_TIMEOUT => Err(NetError::Timeout),
            _ => Err(NetError::RequestFailed(format!(
                "HTTP {}: {}",
                response.status(),
                response.status().canonical_reason().unwrap_or("Unknown")
            ))),
        }
    }
}

/// Parse URL
pub fn parse_url(url: &str) -> Result<url::Url, NetError> {
    url::Url::parse(url).map_err(|e| NetError::InvalidUrl(e.to_string()))
}
