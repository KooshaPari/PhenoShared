//! Client for a *running* `brokerd`.
//!
//! The MCP bridge must never be a second lease authority. When a daemon address
//! is configured this module lets the tools act on the daemon's authority over
//! its HTTP API instead of opening an in-process
//! [`substrate_browser_broker::Broker`] on the local state root.
//!
//! # The surface this client speaks
//!
//! Reads: `GET /healthz`, `GET /v1/leases`, `GET /v1/sessions`,
//! `GET /v1/view/{id}`, `GET /v1/view/{id}/png`.
//!
//! Mutations: `POST /v1/leases` (acquire), `POST /v1/leases/{id}/release`,
//! `POST /v1/leases/reap`, `POST /v1/profiles/purge`. The daemon validates the
//! bearer token on every one of them, validates the fencing token before it
//! tears anything down, and keeps the acquired browser itself - this client
//! never owns a browser, so there is nothing to leak when it disconnects.
//!
//! # What this client refuses to do
//!
//! An unreachable daemon is an error, never an invitation to mutate a different
//! authority. Silently falling back to a local broker - one the daemon does not
//! serve - is exactly the bug this crate exists to prevent, so every failure to
//! reach `BROKERD_URL` is reported as such and names the variable to fix.
//!
//! # Trusting the daemon's certificate
//!
//! A daemon that serves HTTPS presents a certificate the machine may not
//! trust. `BROKERD_CA` names a PEM file holding the certificate to pin; it is
//! added to the client's trust roots, so the daemon's identity is bound to the
//! certificate it was started with and nothing has to be installed into the
//! machine's trust store. A rejected certificate and a mis-pointed
//! `BROKERD_CA` are reported as themselves, never as an unreachable daemon.

use std::{fmt, time::Duration};

use serde::{de::DeserializeOwned, Deserialize, Serialize};
use substrate_browser::{BrowserError, Lease};
use substrate_browser_broker::{BrokerError, LiveSessionInfo};

use crate::{
    ca,
    config::RemoteConfig,
    remote::{RemoteAcquired, RemotePurged, RemoteReaped, RemoteReleased},
};

/// Environment variable naming a running `brokerd`, for example
/// `http://127.0.0.1:8787`.
pub const URL_ENV: &str = "BROKERD_URL";

/// Environment variable carrying the bearer token `brokerd` expects.
///
/// Optional: a loopback daemon started without `--token` needs none.
pub const TOKEN_ENV: &str = "BROKERD_TOKEN";

/// Environment variable naming a PEM file holding the certificate to trust
/// for the daemon's TLS connection, for example `/etc/brokerd/cert.pem`.
///
/// Optional: a daemon whose certificate the machine already trusts needs
/// none. When it is set, that certificate is *added* to the client's trust
/// roots rather than swapped for them, so a daemon with a publicly trusted
/// certificate stays reachable and the daemon's identity stays bound to the
/// certificate it was started with.
pub const CA_ENV: &str = "BROKERD_CA";

/// Per-request timeout for the daemon client, in seconds.
const REQUEST_TIMEOUT: Duration = Duration::from_secs(10);

/// Connection timeout. Short so a wrong address fails loudly and quickly.
const CONNECT_TIMEOUT: Duration = Duration::from_secs(3);

/// Refuse an operation, with the reason the caller has to act on.
pub(crate) fn refused(message: impl Into<String>) -> BrokerError {
    BrokerError::State(BrowserError::Refused(message.into()))
}

/// A client for a running `brokerd`.
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
    /// Build a client. No network traffic happens here: failures to reach the
    /// daemon surface on the first call, so a caller cannot mistake "client
    /// built" for "daemon reachable".
    ///
    /// When the configuration pins a CA, that certificate is read from disk
    /// and joins the client's trust roots. It is added, never swapped for
    /// them, so a daemon with a publicly trusted certificate keeps answering.
    pub fn new(config: RemoteConfig) -> Result<Self, BrokerError> {
        let mut builder = reqwest::Client::builder()
            .connect_timeout(CONNECT_TIMEOUT)
            .timeout(REQUEST_TIMEOUT);
        if let Some(path) = config.ca_path() {
            for certificate in ca::pinned_certificates(path)? {
                builder = builder.add_root_certificate(certificate);
            }
        }
        let http = builder.build().map_err(|err| {
            // The pinned certificate is the only thing this client added, so a
            // failure here is about that certificate.
            match config.ca_path() {
                Some(path) => ca::unusable_certificate(path, &err),
                None => refused(format!("cannot build a brokerd HTTP client: {err}")),
            }
        })?;
        Ok(Self { config, http })
    }

    /// The daemon this client talks to.
    pub fn config(&self) -> &RemoteConfig {
        &self.config
    }

    /// Present the configured credential, when there is one.
    fn authorised(&self, request: reqwest::RequestBuilder) -> reqwest::RequestBuilder {
        match self.config.token() {
            Some(token) => request.bearer_auth(token),
            None => request,
        }
    }

    /// Explain why a request produced no response.
    ///
    /// A rejected TLS certificate is not an unreachable daemon: the daemon
    /// answered the handshake and this client refused the certificate it
    /// presented. That case names `BROKERD_CA`, because pinning the daemon's
    /// certificate is the repair. Every other failure keeps the wording that
    /// says the daemon was never reached.
    fn explain_failure(&self, err: &reqwest::Error) -> BrokerError {
        match ca::certificate_rejection(err) {
            Some(detail) => refused(format!(
                "brokerd at {} rejected the TLS certificate ({detail}); point {CA_ENV} at the PEM \
                 certificate the daemon was started with",
                self.config.base_url()
            )),
            None => {
                // Fail loudly, never fall back to a local broker: the operator
                // configured a daemon, so a different authority would be a lie.
                refused(format!(
                    "brokerd at {} is configured via {URL_ENV} but unreachable ({err}); refusing \
                     to fall back to an in-process broker. Fix the address or unset {URL_ENV}.",
                    self.config.base_url()
                ))
            },
        }
    }

    /// Send `request` and decode the JSON body, or explain precisely why not.
    async fn send_json<T>(
        &self,
        request: reqwest::RequestBuilder,
        url: &str,
    ) -> Result<T, BrokerError>
    where
        T: DeserializeOwned,
    {
        let response = request
            .send()
            .await
            .map_err(|err| self.explain_failure(&err))?;

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
                self.config.base_url()
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

    async fn get_json<T>(&self, path: &str) -> Result<T, BrokerError>
    where
        T: DeserializeOwned,
    {
        let url = self.config.endpoint(path);
        let request = self.authorised(self.http.get(&url));
        self.send_json(request, &url).await
    }

    async fn post_json<T, B>(&self, path: &str, body: &B) -> Result<T, BrokerError>
    where
        T: DeserializeOwned,
        B: Serialize + ?Sized,
    {
        let url = self.config.endpoint(path);
        let request = self.authorised(self.http.post(&url)).json(body);
        self.send_json(request, &url).await
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

    /// Ask the daemon to acquire a lease and launch the browser itself.
    ///
    /// The browser lives on the daemon, so nothing is returned that this process
    /// could hold, leak or tear down.
    pub async fn acquire(
        &self,
        principal: &str,
        profile: &str,
        session: &str,
        holder: &str,
        ttl_ms: u64,
    ) -> Result<RemoteAcquired, BrokerError> {
        #[derive(Serialize)]
        struct Body<'a> {
            principal: &'a str,
            profile: &'a str,
            session: &'a str,
            holder: &'a str,
            ttl_ms: u64,
        }
        self.post_json(
            "/v1/leases",
            &Body {
                principal,
                profile,
                session,
                holder,
                ttl_ms,
            },
        )
        .await
    }

    /// Ask the daemon to release `lease_id`.
    ///
    /// The daemon validates `fencing_token` before it mutates anything, so a
    /// stale token tears nothing down.
    pub async fn release(
        &self,
        lease_id: &str,
        fencing_token: u64,
    ) -> Result<RemoteReleased, BrokerError> {
        #[derive(Serialize)]
        struct Body {
            fencing_token: u64,
        }
        self.post_json(
            &format!("/v1/leases/{lease_id}/release"),
            &Body { fencing_token },
        )
        .await
    }

    /// Ask the daemon to reap expired sessions and lease records.
    pub async fn reap(&self) -> Result<RemoteReaped, BrokerError> {
        #[derive(Serialize)]
        struct Body {}
        self.post_json("/v1/leases/reap", &Body {}).await
    }

    /// Ask the daemon to delete a profile's data.
    ///
    /// `confirm` is forwarded as sent: the daemon, not this client, owns the
    /// guard, so a false value is refused there rather than silently dropped.
    pub async fn purge(
        &self,
        principal: &str,
        profile: &str,
        confirm: bool,
    ) -> Result<RemotePurged, BrokerError> {
        #[derive(Serialize)]
        struct Body<'a> {
            principal: &'a str,
            profile: &'a str,
            confirm: bool,
        }
        self.post_json(
            "/v1/profiles/purge",
            &Body {
                principal,
                profile,
                confirm,
            },
        )
        .await
    }
}
