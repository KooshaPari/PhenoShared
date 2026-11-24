//! HTTP client wrapper for making outbound REST requests.
//!
//! `RestClient` wraps [`reqwest::Client`] with convenience methods for the
//! common HTTP verbs, automatic JSON serialization/deserialization, and
//! integration with the crate's [`Error`] type.

use std::time::Duration;

use reqwest::Client;
use serde::de::DeserializeOwned;

use crate::error::{Error, Result};

/// A convenience HTTP client for REST APIs.
///
/// Wraps [`reqwest::Client`] with typed request/response methods and
/// integration with [`crate::Error`].
///
/// # Examples
///
/// ```no_run
/// # use apisync::clients::RestClient;
/// # async fn example() -> Result<(), apisync::error::Error> {
/// let client = RestClient::new("https://api.example.com");
/// let items: Vec<serde_json::Value> = client.get("/items").await?;
/// # Ok(())
/// # }
/// ```
#[derive(Debug, Clone)]
pub struct RestClient {
    client: Client,
    base_url: String,
}

impl RestClient {
    /// Create a new client with the given base URL.
    ///
    /// Uses default [`reqwest::Client`] settings (no proxy, standard timeouts).
    pub fn new(base_url: impl Into<String>) -> Self {
        Self { client: Client::new(), base_url: base_url.into() }
    }

    /// Create a new client with custom [`reqwest::Client`] settings.
    pub fn with_client(client: Client, base_url: impl Into<String>) -> Self {
        Self { client, base_url: base_url.into() }
    }

    /// Create a builder with a connection timeout.
    pub fn with_timeout(base_url: impl Into<String>, timeout: Duration) -> Self {
        let client = Client::builder().timeout(timeout).build().expect("failed to build reqwest client");
        Self { client, base_url: base_url.into() }
    }

    /// Return a reference to the underlying [`reqwest::Client`].
    pub fn inner(&self) -> &Client {
        &self.client
    }

    /// Return the base URL.
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    fn url(&self, path: &str) -> String {
        format!("{}{}", self.base_url.trim_end_matches('/'), path)
    }

    /// Send a GET request and deserialize the response body as JSON.
    pub async fn get<T: DeserializeOwned>(&self, path: &str) -> Result<T> {
        let resp = self.client.get(self.url(path)).send().await?;
        check_status(&resp)?;
        let value = resp.json().await?;
        Ok(value)
    }

    /// Send a POST request with a JSON body and deserialize the response.
    pub async fn post<B: serde::Serialize, T: DeserializeOwned>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T> {
        let resp = self.client.post(self.url(path)).json(body).send().await?;
        check_status(&resp)?;
        let value = resp.json().await?;
        Ok(value)
    }

    /// Send a PUT request with a JSON body and deserialize the response.
    pub async fn put<B: serde::Serialize, T: DeserializeOwned>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T> {
        let resp = self.client.put(self.url(path)).json(body).send().await?;
        check_status(&resp)?;
        let value = resp.json().await?;
        Ok(value)
    }

    /// Send a PATCH request with a JSON body and deserialize the response.
    pub async fn patch<B: serde::Serialize, T: DeserializeOwned>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T> {
        let resp = self.client.patch(self.url(path)).json(body).send().await?;
        check_status(&resp)?;
        let value = resp.json().await?;
        Ok(value)
    }

    /// Send a DELETE request and deserialize the response.
    pub async fn delete<T: DeserializeOwned>(&self, path: &str) -> Result<T> {
        let resp = self.client.delete(self.url(path)).send().await?;
        check_status(&resp)?;
        let value = resp.json().await?;
        Ok(value)
    }

    /// Send a GET request and return the raw response body as bytes.
    pub async fn get_raw(&self, path: &str) -> Result<Vec<u8>> {
        let resp = self.client.get(self.url(path)).send().await?;
        check_status(&resp)?;
        let bytes = resp.bytes().await?.to_vec();
        Ok(bytes)
    }

    /// Send a POST request with a raw body and return the raw response.
    pub async fn post_raw(&self, path: &str, body: Vec<u8>, content_type: &str) -> Result<Vec<u8>> {
        let resp = self
            .client
            .post(self.url(path))
            .header("Content-Type", content_type)
            .body(body)
            .send()
            .await?;
        check_status(&resp)?;
        let bytes = resp.bytes().await?.to_vec();
        Ok(bytes)
    }
}

/// Check that a response status is 2xx; return an [`Error::Http`] otherwise.
fn check_status(resp: &reqwest::Response) -> Result<()> {
    if resp.status().is_success() {
        Ok(())
    } else {
        let status = resp.status().as_u16();
        Err(Error::Http { status, body: None })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_url_construction() {
        let client = RestClient::new("https://api.example.com");
        assert_eq!(client.url("/items"), "https://api.example.com/items");
        assert_eq!(client.url("items"), "https://api.example.comitems");
    }

    #[test]
    fn test_url_trailing_slash() {
        let client = RestClient::new("https://api.example.com/");
        assert_eq!(client.url("/items"), "https://api.example.com/items");
    }

    #[test]
    fn test_base_url_accessor() {
        let client = RestClient::new("https://api.example.com");
        assert_eq!(client.base_url(), "https://api.example.com");
    }

    #[test]
    fn test_client_is_clone() {
        let client = RestClient::new("https://api.example.com");
        let _cloned = client.clone();
    }

    #[test]
    fn test_client_is_debug() {
        let client = RestClient::new("https://api.example.com");
        let _dbg = format!("{:?}", client);
    }

    #[test]
    fn test_with_client() {
        let req_client = reqwest::Client::new();
        let client = RestClient::with_client(req_client, "https://api.test.com");
        assert_eq!(client.base_url(), "https://api.test.com");
        let _ = client.inner();
    }

    #[test]
    fn test_with_timeout() {
        let client = RestClient::with_timeout("https://api.test.com", Duration::from_secs(5));
        assert_eq!(client.base_url(), "https://api.test.com");
        let _ = client.inner();
    }

    #[test]
    fn test_inner() {
        let client = RestClient::new("https://api.example.com");
        let inner = client.inner();
        // Verify it returns a valid reqwest::Client reference by cloning it
        let _cloned = inner.clone();
    }
    #[test]
    fn test_url_nested_path() {
        let client = RestClient::new("https://api.example.com/v1");
        assert_eq!(client.url("/items"), "https://api.example.com/v1/items");
    }

    #[test]
    fn test_url_empty_path() {
        let client = RestClient::new("https://api.example.com");
        assert_eq!(client.url(""), "https://api.example.com");
    }

    #[test]
    fn test_clone_preserves_url() {
        let client = RestClient::new("https://api.example.com");
        let cloned = client.clone();
        assert_eq!(cloned.base_url(), client.base_url());
    }
}
