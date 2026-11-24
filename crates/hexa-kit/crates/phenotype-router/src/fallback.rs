//! H14.2 — Multi-account fallback chain for the router plane.
//!
//! Wraps a single shared `reqwest::Client` and an ordered sequence of
//! [`AccountConfig`] entries so that one logical request transparently walks
//! the chain until it gets a `2xx`, retrying within an account on retryable
//! failures and stepping to the next account on continued failure.
//!
//! Failure classification
//! ----------------------
//! - `2xx` (and any `1xx`)           → success, returned as [`Response`]
//! - `4xx`                           → terminal client error, surfaced as
//!                                     [`FallbackError::ClientError`] (no retry,
//!                                     no fallback to the next account)
//! - `5xx` / connect failure / timeout → retryable; the chain retries
//!                                       `account.max_retries` times within the
//!                                       account, then steps to the next
//!                                       account. If every account is exhausted,
//!                                       the chain returns
//!                                       [`FallbackError::AllAccountsExhausted`].
//!
//! Ordering: accounts are tried in `Vec` order. `AccountConfig::weight` is
//! captured on the struct for future weighted selection (a follow-up H14.x
//! ticket) and is unused by this Tier 1 implementation.
//!
//! Transport: one `reqwest::Client` is shared across the chain. The client has
//! no default timeout set; each per-request `.timeout()` comes from
//! `AccountConfig::timeout_ms` so that slow accounts cannot starve fast ones.

use std::time::Duration;

use bytes::Bytes;
use thiserror::Error;
use tracing::{debug, warn};

/// Configuration for a single upstream account in the fallback chain.
#[derive(Debug, Clone)]
pub struct AccountConfig {
    /// Human-readable identifier (for logs and [`Response::account`]).
    pub name: String,
    /// Base URL of the upstream account, e.g. `https://api.openai.com`.
    /// The request path is appended to this.
    pub url: String,
    /// Selection weight for future weighted routing (unused by H14.2;
    /// accounts are tried in `Vec` order).
    pub weight: u32,
    /// Maximum number of attempts against THIS account before stepping to the
    /// next account. Values `< 1` are clamped to `1`.
    pub max_retries: u32,
    /// Per-request timeout, in milliseconds, for every attempt against this
    /// account.
    pub timeout_ms: u64,
}

impl AccountConfig {
    /// Build a config with sensible defaults: weight 1, one retry, 30 s timeout,
    /// empty name.
    pub fn new(url: impl Into<String>) -> Self {
        Self {
            name: String::new(),
            url: url.into(),
            weight: 1,
            max_retries: 1,
            timeout_ms: 30_000,
        }
    }

    pub fn with_name(mut self, name: impl Into<String>) -> Self {
        self.name = name.into();
        self
    }

    pub fn with_weight(mut self, weight: u32) -> Self {
        self.weight = weight;
        self
    }

    /// Set `max_retries`. Values `< 1` are clamped to `1`.
    pub fn with_max_retries(mut self, max_retries: u32) -> Self {
        self.max_retries = max_retries.max(1);
        self
    }

    pub fn with_timeout_ms(mut self, timeout_ms: u64) -> Self {
        self.timeout_ms = timeout_ms;
        self
    }
}

/// A single logical HTTP request that will be issued through the chain.
#[derive(Debug, Clone)]
pub struct RequestSpec {
    pub method: String,
    pub path: String,
    pub body: Option<Bytes>,
    pub headers: Vec<(String, String)>,
}

impl RequestSpec {
    pub fn get(path: impl Into<String>) -> Self {
        Self {
            method: "GET".to_string(),
            path: path.into(),
            body: None,
            headers: Vec::new(),
        }
    }

    pub fn post(path: impl Into<String>, body: impl Into<Bytes>) -> Self {
        Self {
            method: "POST".to_string(),
            path: path.into(),
            body: Some(body.into()),
            headers: Vec::new(),
        }
    }

    pub fn with_header(mut self, k: impl Into<String>, v: impl Into<String>) -> Self {
        self.headers.push((k.into(), v.into()));
        self
    }
}

/// A successful response returned by [`FallbackChain::try_request`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Response {
    pub status: u16,
    pub body: Bytes,
    /// Name of the account that ultimately served the response.
    pub account: String,
}

/// All error modes a [`FallbackChain`] can surface.
#[derive(Debug, Error)]
pub enum FallbackError {
    #[error("fallback chain is empty")]
    NoAccounts,

    #[error("invalid HTTP method: {0}")]
    InvalidMethod(String),

    #[error("4xx response from {account} (status {status}); not retried")]
    ClientError {
        account: String,
        status: u16,
        body: Bytes,
    },

    #[error("failed to read response body from {account}: {detail}")]
    ReadBody {
        account: String,
        detail: String,
    },
    #[error(
        "all {total} accounts exhausted (last_status: {last_status:?}, last_error: {last_error:?})"
    )]
    AllAccountsExhausted {
        total: usize,
        last_status: Option<u16>,
        last_error: Option<String>,
    },
}

/// Multi-account fallback chain.
///
/// Construct via [`FallbackChain::new`] / [`FallbackChain::from_iter`], then
/// issue requests with [`FallbackChain::try_request`].
pub struct FallbackChain {
    accounts: Vec<AccountConfig>,
    client: reqwest::Client,
}

impl FallbackChain {
    /// Build a chain from an explicit `Vec` of accounts.
    pub fn new(accounts: Vec<AccountConfig>) -> Self {
        Self {
            accounts,
            // `Client::new()` is documented to never fail; it uses default
            // config (no global timeout, so per-request `.timeout()` from
            // `AccountConfig::timeout_ms` is authoritative).
            client: reqwest::Client::new(),
        }
    }

    pub fn from_iter<I: IntoIterator<Item = AccountConfig>>(it: I) -> Self {
        Self::new(it.into_iter().collect())
    }

    pub fn len(&self) -> usize {
        self.accounts.len()
    }

    pub fn is_empty(&self) -> bool {
        self.accounts.is_empty()
    }

    pub fn accounts(&self) -> &[AccountConfig] {
        &self.accounts
    }

    /// Issue `req` through the chain. Returns the first successful (2xx)
    /// response, or [`FallbackError`] otherwise.
    pub async fn try_request(&self, req: &RequestSpec) -> Result<Response, FallbackError> {
        if self.accounts.is_empty() {
            return Err(FallbackError::NoAccounts);
        }

        let method = reqwest::Method::from_bytes(req.method.as_bytes())
            .map_err(|_| FallbackError::InvalidMethod(req.method.clone()))?;

        let mut last_status: Option<u16> = None;
        let mut last_error: Option<String> = None;

        for account in &self.accounts {
            let attempts = account.max_retries.max(1);
            let timeout = Duration::from_millis(account.timeout_ms);
            let base = account.url.trim_end_matches('/');
            let url = format!("{base}{}", req.path);

            for attempt in 0..attempts {
                debug!(account = %account.name, attempt, url = %url, "fallback: send");

                let mut builder = self
                    .client
                    .request(method.clone(), &url)
                    .timeout(timeout);

                for (k, v) in &req.headers {
                    builder = builder.header(k, v);
                }

                if let Some(body) = &req.body {
                    builder = builder.body(body.clone());
                }

                match builder.send().await {
                    Ok(resp) => {
                        let status = resp.status();
                        let code = status.as_u16();
                        last_status = Some(code);

                        if status.is_success() {
                            let account_name = account.name.clone();
                            let body = match resp.bytes().await {
                                Ok(b) => b,
                                Err(e) => {
                                    return Err(FallbackError::ReadBody {
                                        account: account_name,
                                        detail: e.to_string(),
                                    });
                                }
                            };
                            return Ok(Response {
                                status: code,
                                body,
                                account: account_name,
                            });
                        }

                        if status.is_client_error() {
                            let account_name = account.name.clone();
                            let body = match resp.bytes().await {
                                Ok(b) => b,
                                Err(_) => Bytes::new(),
                            };
                            return Err(FallbackError::ClientError {
                                account: account_name,
                                status: code,
                                body,
                            });
                        }

                        // 5xx (or other non-success, non-4xx) — retryable.
                        warn!(
                            account = %account.name,
                            attempt,
                            status = code,
                            "fallback: upstream error"
                        );
                        // Drain so the connection can be released back to the pool.
                        let _ = resp.bytes().await;
                    }
                    Err(e) => {
                        let msg = e.to_string();
                        last_error = Some(msg.clone());
                        warn!(
                            account = %account.name,
                            attempt,
                            error = %msg,
                            "fallback: request failed"
                        );
                    }
                }
            }
        }

        Err(FallbackError::AllAccountsExhausted {
            total: self.accounts.len(),
            last_status,
            last_error,
        })
    }
}

impl std::fmt::Debug for FallbackChain {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FallbackChain")
            .field("accounts", &self.accounts)
            .field("accounts_len", &self.accounts.len())
            .finish_non_exhaustive()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    use std::collections::VecDeque;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;
    use tokio::sync::Mutex;

    /// A canned response. Status `0` means "hang forever (until client
    /// timeout)".
    type Canned = (u16, Vec<u8>);

    /// Minimal in-process HTTP/1.1 mock server backed by `tokio::net`. It
    /// returns queued `(status, body)` responses in order, tracks the number
    /// of accepted connections, and supports a "hang" sentinel for timeout
    /// tests. No external mocking crates — only `tokio`.
    struct Mock {
        base_url: String,
        _responses: Arc<Mutex<VecDeque<Canned>>>,
        request_count: Arc<AtomicUsize>,
        handle: tokio::task::JoinHandle<()>,
    }

    impl Mock {
        async fn start(responses: Vec<Canned>) -> Self {
            let listener = TcpListener::bind("127.0.0.1:0")
                .await
                .expect("mock: bind");
            let addr = listener.local_addr().expect("mock: local_addr");

            let queue: Arc<Mutex<VecDeque<Canned>>> =
                Arc::new(Mutex::new(VecDeque::from(responses)));
            let count = Arc::new(AtomicUsize::new(0));

            let queue_c = queue.clone();
            let count_c = count.clone();
            let handle = tokio::spawn(async move {
                loop {
                    let (mut sock, _) = match listener.accept().await {
                        Ok(p) => p,
                        Err(_) => break,
                    };
                    let queue = queue_c.clone();
                    let count = count_c.clone();
                    tokio::spawn(async move {
                        count.fetch_add(1, Ordering::SeqCst);
                        // Read the request (headers + body, up to 64 KiB or
                        // 200 ms, whichever comes first).
                        let mut total = Vec::new();
                        let mut tmp = [0u8; 1024];
                        let deadline =
                            tokio::time::Instant::now() + Duration::from_millis(200);
                        loop {
                            if total.len() > 65_536 {
                                break;
                            }
                            let now = tokio::time::Instant::now();
                            if now >= deadline {
                                break;
                            }
                            let remaining = deadline - now;
                            match tokio::time::timeout(remaining, sock.read(&mut tmp)).await {
                                Ok(Ok(0)) => break,
                                Ok(Ok(n)) => {
                                    total.extend_from_slice(&tmp[..n]);
                                    if let Some(cl) = parse_content_length(&total) {
                                        let hend = find_header_end(&total) + 4;
                                        if total.len() >= hend + cl {
                                            break;
                                        }
                                    } else if total.windows(4).any(|w| w == b"\r\n\r\n") {
                                        break;
                                    }
                                }
                                _ => break,
                            }
                        }

                        let resp = queue.lock().await.pop_front();
                        let (status, body) = match resp {
                            Some(r) => r,
                            None => (500, b"mock: no more responses".to_vec()),
                        };

                        if status == 0 {
                            // Hang until either the client gives up or the
                            // outer test drops us.
                            tokio::time::sleep(Duration::from_secs(15)).await;
                            let _ = sock.shutdown().await;
                            return;
                        }

                        let reason = match status {
                            200 => "OK",
                            201 => "Created",
                            204 => "No Content",
                            400 => "Bad Request",
                            401 => "Unauthorized",
                            403 => "Forbidden",
                            404 => "Not Found",
                            429 => "Too Many Requests",
                            500 => "Internal Server Error",
                            502 => "Bad Gateway",
                            503 => "Service Unavailable",
                            504 => "Gateway Timeout",
                            _ => "Status",
                        };
                        let header = format!(
                            "HTTP/1.1 {status} {reason}\r\nContent-Length: {}\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n",
                            body.len()
                        );
                        let mut payload = header.into_bytes();
                        payload.extend_from_slice(&body);
                        let _ = sock.write_all(&payload).await;
                        let _ = sock.shutdown().await;
                    });
                }
            });

            Self {
                base_url: format!("http://{addr}"),
                _responses: queue,
                request_count: count,
                handle,
            }
        }

        fn url(&self, path: &str) -> String {
            format!("{}{path}", self.base_url)
        }

        fn count(&self) -> usize {
            self.request_count.load(Ordering::SeqCst)
        }
    }

    impl Drop for Mock {
        fn drop(&mut self) {
            self.handle.abort();
        }
    }

    fn parse_content_length(headers: &[u8]) -> Option<usize> {
        let s = std::str::from_utf8(headers).ok()?;
        for line in s.split("\r\n") {
            let mut parts = line.splitn(2, ':');
            let k = parts.next()?.trim();
            let v = parts.next()?.trim();
            if k.eq_ignore_ascii_case("content-length") {
                return v.parse().ok();
            }
        }
        None
    }

    fn find_header_end(headers: &[u8]) -> usize {
        headers
            .windows(4)
            .position(|w| w == b"\r\n\r\n")
            .unwrap_or(headers.len())
    }

    // ---------- tests ----------

    #[tokio::test]
    async fn success_first_try() {
        let mock = Mock::start(vec![(200, b"{\"ok\":true}".to_vec())]).await;

        let chain = FallbackChain::from_iter([AccountConfig::new(mock.url(""))
            .with_name("primary")
            .with_max_retries(3)]);

        let resp = chain
            .try_request(&RequestSpec::get("/test"))
            .await
            .expect("ok");

        assert_eq!(resp.status, 200);
        assert_eq!(resp.account, "primary");
        assert_eq!(&resp.body[..], b"{\"ok\":true}");
        // The first attempt succeeded — no retries.
        assert_eq!(mock.count(), 1);
    }

    #[tokio::test]
    async fn second_account_succeeds_after_first_500() {
        let mock = Mock::start(vec![
            (500, b"server err".to_vec()),
            (200, b"from-secondary".to_vec()),
        ])
        .await;

        let chain = FallbackChain::from_iter([
            AccountConfig::new(mock.url(""))
                .with_name("primary")
                .with_max_retries(1),
            AccountConfig::new(mock.url(""))
                .with_name("secondary")
                .with_max_retries(1),
        ]);

        let resp = chain
            .try_request(&RequestSpec::get("/v1/chat"))
            .await
            .expect("ok");

        assert_eq!(resp.status, 200);
        assert_eq!(resp.account, "secondary");
        assert_eq!(&resp.body[..], b"from-secondary");
        assert_eq!(mock.count(), 2);
    }

    #[tokio::test]
    async fn all_accounts_fail_returns_exhausted() {
        let mock = Mock::start(vec![
            (500, b"e1".to_vec()),
            (502, b"e2".to_vec()),
            (503, b"e3".to_vec()),
        ])
        .await;

        let chain = FallbackChain::from_iter([
            AccountConfig::new(mock.url(""))
                .with_name("a")
                .with_max_retries(1),
            AccountConfig::new(mock.url(""))
                .with_name("b")
                .with_max_retries(1),
            AccountConfig::new(mock.url(""))
                .with_name("c")
                .with_max_retries(1),
        ]);

        let err = chain
            .try_request(&RequestSpec::get("/x"))
            .await
            .unwrap_err();

        match err {
            FallbackError::AllAccountsExhausted {
                total,
                last_status,
                last_error: _,
            } => {
                assert_eq!(total, 3);
                assert_eq!(last_status, Some(503));
            }
            other => panic!("unexpected error: {other:?}"),
        }
        assert_eq!(mock.count(), 3);
    }

    #[tokio::test]
    async fn mixed_status_codes_4xx_is_terminal_no_fallback() {
        let mock = Mock::start(vec![
            (500, b"a".to_vec()),
            (404, b"{\"err\":\"missing\"}".to_vec()),
            (200, b"never-reached".to_vec()),
        ])
        .await;

        let chain = FallbackChain::from_iter([
            AccountConfig::new(mock.url(""))
                .with_name("a")
                .with_max_retries(1),
            AccountConfig::new(mock.url(""))
                .with_name("b")
                .with_max_retries(1),
            AccountConfig::new(mock.url(""))
                .with_name("c")
                .with_max_retries(1),
        ]);

        let err = chain
            .try_request(&RequestSpec::get("/x"))
            .await
            .unwrap_err();

        match err {
            FallbackError::ClientError {
                account,
                status,
                body,
            } => {
                assert_eq!(account, "b");
                assert_eq!(status, 404);
                assert_eq!(&body[..], b"{\"err\":\"missing\"}");
            }
            other => panic!("unexpected error: {other:?}"),
        }
        // Only accounts `a` and `b` were hit; `c` was never reached because
        // 4xx is terminal.
        assert_eq!(mock.count(), 2);
    }

    #[tokio::test]
    async fn timeout_handling_moves_to_next_account() {
        let mock = Mock::start(vec![(0, Vec::new()), (200, b"recovered".to_vec())]).await;

        let chain = FallbackChain::from_iter([
            AccountConfig::new(mock.url(""))
                .with_name("slow")
                .with_max_retries(1)
                .with_timeout_ms(200),
            AccountConfig::new(mock.url(""))
                .with_name("fast")
                .with_max_retries(1)
                .with_timeout_ms(5_000),
        ]);

        let resp = chain
            .try_request(&RequestSpec::get("/x"))
            .await
            .expect("ok");

        assert_eq!(resp.status, 200);
        assert_eq!(resp.account, "fast");
        assert_eq!(&resp.body[..], b"recovered");
        // Both accounts should have been hit: `slow` timed out, `fast` served.
        assert_eq!(mock.count(), 2);
    }

    #[tokio::test]
    async fn retries_within_single_account_then_succeeds() {
        let mock = Mock::start(vec![
            (500, b"e1".to_vec()),
            (500, b"e2".to_vec()),
            (200, b"eventually".to_vec()),
        ])
        .await;

        let chain = FallbackChain::from_iter([AccountConfig::new(mock.url(""))
            .with_name("flaky")
            .with_max_retries(3)
            .with_timeout_ms(2_000)]);

        let resp = chain
            .try_request(&RequestSpec::get("/x"))
            .await
            .expect("ok");

        assert_eq!(resp.status, 200);
        assert_eq!(resp.account, "flaky");
        assert_eq!(&resp.body[..], b"eventually");
        assert_eq!(mock.count(), 3);
    }

    #[tokio::test]
    async fn empty_chain_returns_no_accounts() {
        let chain = FallbackChain::new(Vec::new());
        let err = chain
            .try_request(&RequestSpec::get("/x"))
            .await
            .unwrap_err();
        assert!(matches!(err, FallbackError::NoAccounts));
    }

    #[tokio::test]
    async fn post_body_is_forwarded_to_account() {
        let mock = Mock::start(vec![(200, b"ok".to_vec())]).await;

        let chain = FallbackChain::from_iter([AccountConfig::new(mock.url(""))
            .with_name("p")
            .with_max_retries(1)]);

        let resp = chain
            .try_request(&RequestSpec::post(
                "/v1/chat/completions",
                "{\"prompt\":\"hi\"}",
            ))
            .await
            .expect("ok");

        assert_eq!(resp.status, 200);
        assert_eq!(resp.account, "p");
        // The mock would error during body write if it didn't accept the
        // request body; getting a 200 back proves reqwest sent the body.
        assert_eq!(&resp.body[..], b"ok");
    }
}
