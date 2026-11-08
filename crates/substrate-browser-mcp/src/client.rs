//! Client for a *running* `brokerd`.
//!
//! The MCP bridge must never be a second lease authority. When a daemon address
//! is configured this module lets the tools read the daemon's authority over its
//! HTTP API instead of opening an in-process [`substrate_browser_broker::Broker`]
//! on the local state root.
//!
//! # The boundary this client is honest about
//!
//! `brokerd`'s HTTP surface is a *viewer*: `GET /healthz`, `GET /v1/leases`,
//! `GET /v1/sessions`, `GET /v1/view/{id}`, `GET /v1/view/{id}/png`. There is no
//! acquire, release, reap or purge route. So a remote configuration is
//! supervision: reads come from the daemon, and every mutation is refused with
//! an explicit error. The alternative - silently mutating a local broker the
//! daemon does not serve - is exactly the bug this crate exists to prevent.

use std::{fmt, time::Duration};

use serde::Deserialize;
use substrate_browser::{BrowserError, Lease};
use substrate_browser_broker::{BrokerError, LiveSessionInfo};

/// Environment variable naming a running `brokerd`, for example
/// `http://127.0.0.1:8787`.
pub const URL_ENV: &str = "BROKERD_URL";

/// Environment variable carrying the bearer token `brokerd` expects.
///
/// Optional: a loopback daemon started without `--token` needs none.
pub const TOKEN_ENV: &str = "BROKERD_TOKEN";

/// Per-request timeout for the daemon client, in seconds.
const REQUEST_TIMEOUT: Duration = Duration::from_secs(10);

/// Connection timeout. Short so a wrong address fails loudly and quickly.
const CONNECT_TIMEOUT: Duration = Duration::from_secs(3);

/// Where a running `brokerd` listens, and how to authenticate to it.
#[derive(Clone, PartialEq, Eq)]
pub struct RemoteConfig {
    base_url: String,
    token: Option<String>,
}

impl fmt::Debug for RemoteConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Never print the token, even at debug level.
        f.debug_struct("RemoteConfig")
            .field("base_url", &self.base_url)
            .field("token", &self.token.as_ref().map(|_| "<redacted>"))
            .finish()
    }
}

impl RemoteConfig {
    /// Configure a daemon at `base_url`, normalising trailing slashes.
    pub fn new(base_url: impl Into<String>, token: Option<String>) -> Self {
        let mut base_url = base_url.into();
        while base_url.ends_with('/') {
            base_url.pop();
        }
        Self {
            base_url,
            token: token.filter(|token| !token.is_empty()),
        }
    }

    /// Read the configuration through `get`, so the precedence is testable
    /// without mutating process-global environment variables.
    pub fn from_lookup(get: impl Fn(&str) -> Option<String>) -> Option<Self> {
        let base_url = get(URL_ENV)?;
        let base_url = base_url.trim();
        if base_url.is_empty() {
            return None;
        }
        Some(Self::new(base_url, get(TOKEN_ENV)))
    }

    /// Read the configuration from the process environment.
    pub fn from_env() -> Option<Self> {
        Self::from_lookup(|name| std::env::var(name).ok())
    }

    /// Daemon base URL, without a trailing slash.
    pub fn base_url(&self) -> &str {
        &self.base_url
    }

    /// Whether a bearer token is configured.
    pub fn has_token(&self) -> bool {
        self.token.is_some()
    }

    fn endpoint(&self, path: &str) -> String {
        format!("{}{path}", self.base_url)
    }
}

fn refused(message: impl Into<String>) -> BrokerError {
    BrokerError::State(BrowserError::Refused(message.into()))
}

/// A read-only view of a running `brokerd`.
pub struct RemoteBroker {
    config: RemoteConfig,
    http: reqwest::Client,
}

impl fmt::Debug for RemoteBroker {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RemoteBroker")
            .field("config", &self.config)
            .finish_non_exhaustive()
    }
}

impl RemoteBroker {
    /// Build a client. No I/O happens here: failures surface on the first call,
    /// so a caller cannot mistake "client built" for "daemon reachable".
    pub fn new(config: RemoteConfig) -> Result<Self, BrokerError> {
        let http = reqwest::Client::builder()
            .connect_timeout(CONNECT_TIMEOUT)
            .timeout(REQUEST_TIMEOUT)
            .build()
            .map_err(|err| refused(format!("cannot build a brokerd HTTP client: {err}")))?;
        Ok(Self { config, http })
    }

    /// The daemon this client talks to.
    pub fn config(&self) -> &RemoteConfig {
        &self.config
    }

    async fn get_json<T>(&self, path: &str) -> Result<T, BrokerError>
    where
        T: for<'de> Deserialize<'de>,
    {
        let url = self.config.endpoint(path);
        let mut request = self.http.get(&url);
        if let Some(token) = &self.config.token {
            request = request.bearer_auth(token);
        }

        let response = request.send().await.map_err(|err| {
            // Fail loudly, never fall back to a local broker: the operator
            // configured a daemon, so a different authority would be a lie.
            refused(format!(
                "brokerd at {} is configured via {URL_ENV} but unreachable ({err}); refusing to \
                 fall back to an in-process broker. Fix the address or unset {URL_ENV}.",
                self.config.base_url
            ))
        })?;

        let status = response.status();
        let body = response.text().await.map_err(|err| {
            refused(format!(
                "brokerd at {url} closed the response body early: {err}"
            ))
        })?;

        if status == reqwest::StatusCode::UNAUTHORIZED {
            return Err(refused(format!(
                "brokerd at {} rejected the credential (401); set {TOKEN_ENV} to the token the \
                 daemon was started with",
                self.config.base_url
            )));
        }
        if !status.is_success() {
            return Err(refused(format!(
                "brokerd at {url} returned {status}: {body}"
            )));
        }
        serde_json::from_str(&body).map_err(|err| {
            refused(format!(
                "brokerd at {url} returned a body this client cannot parse: {err}"
            ))
        })
    }

    /// Every lease record the daemon's authority holds.
    pub async fn leases(&self) -> Result<Vec<Lease>, BrokerError> {
        #[derive(Deserialize)]
        struct Envelope {
            leases: Vec<Lease>,
        }
        Ok(self.get_json::<Envelope>("/v1/leases").await?.leases)
    }

    /// The daemon's live browser sessions.
    pub async fn live(&self) -> Result<Vec<LiveSessionInfo>, BrokerError> {
        #[derive(Deserialize)]
        struct Envelope {
            sessions: Vec<LiveSessionInfo>,
        }
        Ok(self.get_json::<Envelope>("/v1/sessions").await?.sessions)
    }

    /// Refusal for an operation `brokerd` exposes no route for.
    pub fn mutation_refusal(&self, action: &str) -> BrokerError {
        refused(format!(
            "brokerd at {} is the configured authority ({URL_ENV}), so `{action}` is refused \
             here: brokerd's HTTP API is read-only (/healthz, /v1/leases, /v1/sessions, \
             /v1/view/*) and has no {action} route. Perform the mutation through brokerd itself, \
             or unset {URL_ENV} so this server works the shared state root directly.",
            self.config.base_url
        ))
    }
}
