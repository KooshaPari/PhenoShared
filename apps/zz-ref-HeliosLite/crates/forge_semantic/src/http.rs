//! Shared HTTP helpers for the remote semantic-memory adapters.
//!
//! The three remote adapters (Supermemory, Letta, Cognee) share an identical
//! shape: a JSON-over-HTTPS POST or DELETE with a Bearer token, a JSON
//! response, and a small set of provider-stable error variants. Centralising
//! the request builder and the `reqwest::Error -> SemanticMemoryError`
//! mapping keeps each adapter file focused on its provider-specific request
//! and response shape.

use std::time::Duration;

use forge_domain::SemanticMemoryError;
use reqwest::header::{ACCEPT, AUTHORIZATION, CONTENT_TYPE, HeaderMap, HeaderValue};
use reqwest::{Client, Response, StatusCode};

/// Default per-request timeout for remote semantic-memory adapters.
///
/// 15s is short enough that a hung provider does not block recall for the
/// full tokio default, and long enough to absorb cold-start cost on Letta
/// cloud's first /v1/agents/{id}/messages call.
pub const DEFAULT_REQUEST_TIMEOUT: Duration = Duration::from_secs(15);

/// Maximum number of attempts (initial + retries) for a single semantic-memory
/// request. Three attempts means one initial plus two retries — short enough
/// to keep user-facing latency bounded, long enough to ride out a one-time
/// provider blip.
pub const DEFAULT_MAX_ATTEMPTS: usize = 3;

/// Starting backoff for the exponential retry. Kept short so the worst-case
/// latency budget is `min_delay * 2^(attempts-2) + per-attempt timeout * attempts`
/// which stays under a few seconds at the default config.
pub const DEFAULT_MIN_DELAY: Duration = Duration::from_millis(100);

/// Hard cap on a single retry's sleep duration. The exponential schedule is
/// allowed to grow up to this ceiling before further growth is clamped.
pub const DEFAULT_MAX_DELAY: Duration = Duration::from_secs(2);

/// Builds a `reqwest::Client` pre-configured with the adapter defaults:
/// JSON accept header, no automatic redirects (we want to see 3xx as a
/// real status), and the per-request timeout.
pub fn build_client() -> Result<reqwest::Client, SemanticMemoryError> {
    reqwest::Client::builder()
        .timeout(DEFAULT_REQUEST_TIMEOUT)
        .redirect(reqwest::redirect::Policy::none())
        .default_headers(default_headers())
        .build()
        .map_err(|err| SemanticMemoryError::Unavailable(format!("build client: {err}")))
}

fn default_headers() -> HeaderMap {
    let mut headers = HeaderMap::new();
    headers.insert(ACCEPT, HeaderValue::from_static("application/json"));
    headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));
    headers
}

/// Returns the bearer-token header pair (`Authorization: Bearer <key>`).
///
/// Returns `Backend { status: 401, ... }` when the caller forgot to wire the
/// API key — the providers themselves return 401, so mapping the local
/// "missing key" case to the same observable error keeps callers' error
/// handling uniform.
pub fn bearer_header(
    api_key: &str,
) -> Result<(reqwest::header::HeaderName, reqwest::header::HeaderValue), SemanticMemoryError> {
    if api_key.trim().is_empty() {
        return Err(SemanticMemoryError::Backend {
            status: 401,
            body: "missing API key".to_string(),
        });
    }
    let value = format!("Bearer {api_key}");
    let header_value = HeaderValue::from_str(&value).map_err(|err| {
        SemanticMemoryError::InvalidResponse(format!("invalid bearer header: {err}"))
    })?;
    Ok((AUTHORIZATION, header_value))
}

/// Maps a `reqwest::Error` to the port's `Unavailable` variant.
///
/// Network-level failures (DNS, TCP reset, TLS handshake, timeout) all flow
/// here. HTTP-level failures (non-2xx status) are handled by the caller via
/// `status_to_error` so the body can be included.
pub fn map_request_error(context: &str, err: reqwest::Error) -> SemanticMemoryError {
    if err.is_timeout() {
        SemanticMemoryError::Unavailable(format!("{context}: timeout"))
    } else if err.is_connect() {
        SemanticMemoryError::Unavailable(format!("{context}: connect failed: {err}"))
    } else if err.is_decode() {
        SemanticMemoryError::InvalidResponse(format!("{context}: decode failed: {err}"))
    } else {
        SemanticMemoryError::Unavailable(format!("{context}: {err}"))
    }
}

/// Converts an HTTP status + body into the port error variant.
///
/// 401 / 403 are auth failures; everything else is a generic backend error.
/// We deliberately do NOT classify 5xx as `Unavailable` here — providers
/// return 5xx on bad input (Letta especially) and the fallback-eligibility
/// decision lives one level up.
pub fn status_to_error(status: u16, body: String) -> SemanticMemoryError {
    SemanticMemoryError::Backend { status, body }
}

/// Convenience: read the response body to string with a tight per-call
/// timeout so a misbehaving provider cannot stall recall indefinitely.
pub async fn read_body(response: reqwest::Response) -> Result<String, SemanticMemoryError> {
    response
        .text()
        .await
        .map_err(|err| map_request_error("read response body", err))
}

/// Returns `true` when the status code is one we should retry: a 429
/// (`Too Many Requests`) or any 5xx server-side failure.
///
/// 4xx other than 429 are client errors (bad input, missing scope) and are
/// not retried — retrying would just produce the same 4xx.
pub fn should_retry_status(status: StatusCode) -> bool {
    status.as_u16() == 429 || status.is_server_error()
}

/// Returns `true` when an error returned from a reqwest call is transient
/// and worth retrying. Today this is just connect/timeout failures — the
/// reqwest client is configured with `redirect(Policy::none())`, so a
/// retry on a redirect is not relevant.
pub fn should_retry_reqwest_error(err: &reqwest::Error) -> bool {
    err.is_timeout() || err.is_connect()
}

/// Sends a single request through the shared `reqwest::Client` with an
/// exponential-backoff retry policy applied to 5xx and 429 responses, plus
/// transient reqwest errors (timeouts, connect failures).
///
/// `build_request` is invoked once per attempt so each retry produces a
/// fresh `reqwest::Request`. This is the right primitive for adapters that
/// serialize a body on each call (cheap, idempotent) — most remote
/// semantic-memory APIs are JSON-only and so qualify.
///
/// `context` is included in the error chain so a failure can be tied back
/// to the calling adapter method without leaking the URL or request body.
pub async fn send_with_retry<F>(
    client: &Client,
    mut build_request: F,
    context: &'static str,
) -> Result<Response, SemanticMemoryError>
where
    F: FnMut() -> Result<reqwest::Request, SemanticMemoryError>,
{
    let mut delay_ms = DEFAULT_MIN_DELAY.as_millis() as u64;
    let mut last_error: Option<RetryHint> = None;
    for attempt in 0..DEFAULT_MAX_ATTEMPTS {
        match build_request() {
            Err(err) => {
                // Request construction itself failed — there is nothing
                // to retry, the body or headers are malformed.
                return Err(err);
            }
            Ok(request) => match client.execute(request).await {
                Ok(response) => {
                    let status = response.status();
                    if should_retry_status(status) {
                        let status_code = status.as_u16();
                        let body = response
                            .text()
                            .await
                            .unwrap_or_else(|_| "<unreadable body>".to_string());
                        last_error = Some(RetryHint::TransientStatus { status: status_code, body });
                    } else {
                        return Ok(response);
                    }
                }
                Err(err) => {
                    if should_retry_reqwest_error(&err) {
                        last_error = Some(RetryHint::Transient(err));
                    } else {
                        return Err(map_request_error(context, err));
                    }
                }
            },
        }

        // If we have another attempt to make, sleep with jitter first.
        if attempt + 1 < DEFAULT_MAX_ATTEMPTS {
            let jitter_ms = fastrand_u64(delay_ms);
            let sleep_for = Duration::from_millis(delay_ms.saturating_add(jitter_ms));
            tokio::time::sleep(sleep_for).await;
            // Exponential growth, clamped to DEFAULT_MAX_DELAY.
            delay_ms = delay_ms
                .saturating_mul(2)
                .min(DEFAULT_MAX_DELAY.as_millis() as u64);
        }
    }

    // All attempts exhausted — surface the last transient error in the
    // same shape the single-attempt path would have.
    match last_error {
        Some(RetryHint::Transient(err)) => Err(map_request_error(context, err)),
        Some(RetryHint::TransientStatus { status, body }) => {
            Err(SemanticMemoryError::Backend { status, body })
        }
        None => Err(SemanticMemoryError::Unavailable(format!(
            "{context}: retry exhausted with no recorded error"
        ))),
    }
}

/// Cheap, dependency-free jitter in `[0, bound)`. Uses `std` PRNG so we
/// do not need a third-party crate to add a few milliseconds of jitter.
fn fastrand_u64(bound_ms: u64) -> u64 {
    use std::cell::Cell;
    use std::num::Wrapping;
    thread_local! {
        // LCG seeded from system time on first use. This is not
        // cryptographic — it only needs to spread retry storms across
        // a few hundred milliseconds.
        static STATE: Cell<Wrapping<u64>> = const { Cell::new(Wrapping(0)) };
    }
    STATE.with(|cell| {
        let mut current = cell.get();
        if current.0 == 0 {
            current = Wrapping(
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_nanos() as u64)
                    .unwrap_or(1),
            );
        }
        current = current * Wrapping(6364136223846793005) + Wrapping(1442695040888963407);
        cell.set(current);
        if bound_ms == 0 {
            0
        } else {
            current.0 % bound_ms
        }
    })
}

/// Sentinel returned from the retry-attempt loop body so the caller can
/// distinguish a "this attempt failed in a way we should retry" arm from
/// the terminal-response arm without re-running the request body reader.
#[derive(Debug)]
enum RetryHint {
    /// A network-level error worth retrying (timeout / connect failure).
    Transient(reqwest::Error),
    /// An HTTP status worth retrying (429 / 5xx).
    TransientStatus { status: u16, body: String },
}

/// Ensures the response status is success (2xx), otherwise maps to
/// `Backend { status, body }`.
pub async fn ensure_success(
    response: reqwest::Response,
) -> Result<reqwest::Response, SemanticMemoryError> {
    let status = response.status();
    if status.is_success() {
        Ok(response)
    } else {
        let status_code = status.as_u16();
        let body = read_body(response)
            .await
            .unwrap_or_else(|_| "<unreadable body>".to_string());
        Err(status_to_error(status_code, body))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bearer_header_rejects_blank_key_as_401() {
        let result = bearer_header("");
        match result {
            Err(SemanticMemoryError::Backend { status: 401, .. }) => {}
            other => panic!("expected 401 backend error, got {other:?}"),
        }
        let result = bearer_header("   ");
        match result {
            Err(SemanticMemoryError::Backend { status: 401, .. }) => {}
            other => panic!("expected 401 backend error, got {other:?}"),
        }
    }

    #[test]
    fn bearer_header_accepts_non_blank_key() {
        let result = bearer_header("sk-test-123");
        assert!(result.is_ok(), "valid key should be accepted");
    }

    #[test]
    fn status_to_error_preserves_status_and_body() {
        let err = status_to_error(503, "service unavailable".to_string());
        match err {
            SemanticMemoryError::Backend { status, body } => {
                assert_eq!(status, 503);
                assert_eq!(body, "service unavailable");
            }
            other => panic!("expected Backend, got {other:?}"),
        }
    }

    #[test]
    fn should_retry_status_returns_true_for_5xx_and_429() {
        assert!(should_retry_status(StatusCode::TOO_MANY_REQUESTS));
        assert!(should_retry_status(StatusCode::SERVICE_UNAVAILABLE));
        assert!(should_retry_status(StatusCode::BAD_GATEWAY));
        assert!(should_retry_status(StatusCode::INTERNAL_SERVER_ERROR));
    }

    #[test]
    fn should_retry_status_returns_false_for_4xx_and_2xx() {
        assert!(!should_retry_status(StatusCode::BAD_REQUEST));
        assert!(!should_retry_status(StatusCode::UNAUTHORIZED));
        assert!(!should_retry_status(StatusCode::FORBIDDEN));
        assert!(!should_retry_status(StatusCode::NOT_FOUND));
        assert!(!should_retry_status(StatusCode::OK));
        assert!(!should_retry_status(StatusCode::CREATED));
    }

    /// Helper that builds a JSON POST request bound for the mockito server
    /// and validates the response status. The closure passed to
    /// `send_with_retry` rebuilds the request on each retry so the helper
    /// exercises the real retry path.
    async fn post_json_retry(
        client: &Client,
        url: String,
    ) -> Result<Response, SemanticMemoryError> {
        let response = send_with_retry(
            client,
            || {
                client
                    .post(&url)
                    .json(&serde_json::json!({"hello": "world"}))
                    .build()
                    .map_err(|err| SemanticMemoryError::InvalidResponse(format!("build: {err}")))
            },
            "test: POST json",
        )
        .await?;
        ensure_success(response).await
    }

    #[tokio::test]
    async fn retry_succeeds_after_a_503() {
        let mut server = mockito::Server::new_async().await;
        let first = server
            .mock("POST", "/")
            .with_status(503)
            .with_body("transient")
            .expect(1)
            .create_async()
            .await;
        let second = server
            .mock("POST", "/")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"ok":true}"#)
            .expect(1)
            .create_async()
            .await;

        let client = build_client().expect("client");
        let url = format!("{}/", server.url());
        let response = post_json_retry(&client, url)
            .await
            .expect("retry should succeed");
        assert_eq!(response.status(), StatusCode::OK);
        first.assert_async().await;
        second.assert_async().await;
    }

    #[tokio::test]
    async fn retry_succeeds_after_a_429() {
        let mut server = mockito::Server::new_async().await;
        let first = server
            .mock("POST", "/")
            .with_status(429)
            .with_body("rate limited")
            .expect(1)
            .create_async()
            .await;
        let second = server
            .mock("POST", "/")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"ok":true}"#)
            .expect(1)
            .create_async()
            .await;

        let client = build_client().expect("client");
        let url = format!("{}/", server.url());
        let response = post_json_retry(&client, url)
            .await
            .expect("retry should succeed");
        assert_eq!(response.status(), StatusCode::OK);
        first.assert_async().await;
        second.assert_async().await;
    }

    #[tokio::test]
    async fn retry_exhausts_after_three_503s_and_returns_backend_error() {
        let mut server = mockito::Server::new_async().await;
        // Mockito `.expect(3)` verifies the endpoint was hit exactly 3
        // times — the initial plus the two retries configured by
        // `DEFAULT_MAX_ATTEMPTS`.
        let mock = server
            .mock("POST", "/")
            .with_status(503)
            .with_body("still down")
            .expect(3)
            .create_async()
            .await;

        let client = build_client().expect("client");
        let url = format!("{}/", server.url());
        let err = post_json_retry(&client, url)
            .await
            .expect_err("retries should be exhausted");
        match err {
            SemanticMemoryError::Backend { status, body } => {
                assert_eq!(status, 503);
                assert!(body.contains("still down"));
            }
            other => panic!("expected Backend(503), got {other:?}"),
        }
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn retry_does_not_fire_for_4xx_responses() {
        let mut server = mockito::Server::new_async().await;
        // A 400 is a client error — no retry should happen, so the mock
        // is expected to be hit exactly once.
        let mock = server
            .mock("POST", "/")
            .with_status(400)
            .with_body("bad input")
            .expect(1)
            .create_async()
            .await;

        let client = build_client().expect("client");
        let url = format!("{}/", server.url());
        let err = post_json_retry(&client, url)
            .await
            .expect_err("400 should not be retried");
        match err {
            SemanticMemoryError::Backend { status, body } => {
                assert_eq!(status, 400);
                assert!(body.contains("bad input"));
            }
            other => panic!("expected Backend(400), got {other:?}"),
        }
        mock.assert_async().await;
    }

    #[tokio::test]
    async fn retry_passes_through_2xx_without_retry() {
        let mut server = mockito::Server::new_async().await;
        // 200 must short-circuit the retry loop. `.expect(1)` confirms
        // the mock was only called once.
        let mock = server
            .mock("POST", "/")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(r#"{"ok":true}"#)
            .expect(1)
            .create_async()
            .await;

        let client = build_client().expect("client");
        let url = format!("{}/", server.url());
        let response = post_json_retry(&client, url)
            .await
            .expect("happy path should succeed");
        assert_eq!(response.status(), StatusCode::OK);
        mock.assert_async().await;
    }
}
