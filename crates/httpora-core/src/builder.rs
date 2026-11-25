use std::collections::HashMap;

use crate::error::HttptoraError;

/// Lightweight HTTP response representation.
#[derive(Debug, Clone)]
pub struct HttpResponse {
    pub status: u16,
    pub body: Vec<u8>,
    pub headers: HashMap<String, String>,
}

impl HttpResponse {
    pub fn ok(&self) -> bool {
        (200..300).contains(&self.status)
    }
}

/// Lightweight HTTP request representation.
#[derive(Debug, Clone)]
pub struct HttpRequest {
    pub method: String,
    pub path: String,
    pub body: Vec<u8>,
    pub headers: HashMap<String, String>,
    pub query: HashMap<String, String>,
}

/// Fluent builder for constructing HTTP responses.
///
/// # Example
///
/// ```
/// use httpora_core::builder::ResponseBuilder;
///
/// let resp = ResponseBuilder::json(200, &serde_json::json!({"ok": true})).unwrap();
/// assert_eq!(resp.status, 200);
/// ```
pub struct ResponseBuilder;

impl ResponseBuilder {
    /// Build a JSON response with Content-Type set.
    #[cfg(feature = "serde_json")]
    pub fn json(status: u16, payload: &serde_json::Value) -> Result<HttpResponse, HttptoraError> {
        let body = serde_json::to_vec(payload).map_err(|e| HttptoraError::ParseError {
            detail: e.to_string(),
        })?;
        let mut headers = HashMap::new();
        headers.insert("Content-Type".into(), "application/json".into());
        Ok(HttpResponse {
            status,
            body,
            headers,
        })
    }

    /// Build a plain-text response.
    pub fn text(status: u16, message: &str) -> HttpResponse {
        let mut headers = HashMap::new();
        headers.insert("Content-Type".into(), "text/plain; charset=utf-8".into());
        HttpResponse {
            status,
            body: message.as_bytes().to_vec(),
            headers,
        }
    }

    /// Build a 204 No Content response.
    pub fn no_content() -> HttpResponse {
        HttpResponse {
            status: 204,
            body: Vec::new(),
            headers: HashMap::new(),
        }
    }

    /// Build an HTTP 429 rate-limit response.
    #[cfg(feature = "serde_json")]
    pub fn rate_limited(retry_after_secs: u64) -> Result<HttpResponse, HttptoraError> {
        use serde_json::json;
        let mut resp = Self::json(429, &json!({"error": "rate_limited"}))?;
        resp.headers
            .insert("Retry-After".into(), retry_after_secs.to_string());
        Ok(resp)
    }
}

/// Helpers for extracting typed data from [`HttpRequest`] objects.
pub struct RequestExtractor;

impl RequestExtractor {
    /// Parse the request body as JSON.
    #[cfg(feature = "serde_json")]
    pub fn json_body(request: &HttpRequest) -> Result<serde_json::Value, HttptoraError> {
        serde_json::from_slice(&request.body).map_err(|e| HttptoraError::ParseError {
            detail: e.to_string(),
        })
    }

    /// Extract the Bearer token from the Authorization header, or `None`.
    pub fn bearer_token(request: &HttpRequest) -> Option<String> {
        let auth = request
            .headers
            .get("Authorization")
            .or_else(|| request.headers.get("authorization"))?;
        auth.strip_prefix("Bearer ").map(str::to_owned)
    }

    /// Case-insensitive header lookup.
    pub fn header<'a>(request: &'a HttpRequest, name: &str) -> Option<&'a str> {
        let lower = name.to_ascii_lowercase();
        request
            .headers
            .iter()
            .find(|(k, _)| k.to_ascii_lowercase() == lower)
            .map(|(_, v)| v.as_str())
    }
}
