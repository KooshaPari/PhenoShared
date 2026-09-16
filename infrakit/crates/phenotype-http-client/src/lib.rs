//! HTTP client

pub mod error;

pub use error::{HttpError, Result};

/// HTTP client wrapper that returns errors for non-2xx responses.
pub struct HttpClient {
    client: reqwest::Client,
}

impl HttpClient {
    pub fn new() -> Self {
        Self {
            client: reqwest::Client::new(),
        }
    }

    /// Fetch a URL and return the response body as a string.
    ///
    /// Returns an error for any non-2xx status code (4xx, 5xx, etc.).
    pub async fn get(&self, url: &str) -> Result<String> {
        let response = self.client.get(url).send().await?;
        let status = response.status();
        if !status.is_success() {
            return Err(HttpError::Http {
                status: status.as_u16(),
                url: url.to_string(),
            });
        }
        Ok(response.text().await?)
    }
}

impl Default for HttpClient {
    fn default() -> Self {
        Self::new()
    }
}
