//! Where a running `brokerd` listens, and how to authenticate to it.
//!
//! The configuration is read through a lookup function rather than straight
//! from the environment, so the precedence between the variables can be
//! checked without mutating process-global state.

use std::{
    fmt,
    path::{Path, PathBuf},
};

use crate::client::{CA_ENV, TOKEN_ENV, URL_ENV};

/// Where a running `brokerd` listens, and how to authenticate to it.
#[derive(Clone, PartialEq, Eq)]
pub struct RemoteConfig {
    base_url: String,
    token: Option<String>,
    ca: Option<PathBuf>,
}

impl fmt::Debug for RemoteConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Never print the token, even at debug level.
        f.debug_struct("RemoteConfig")
            .field("base_url", &self.base_url)
            .field("token", &self.token.as_ref().map(|_| "<redacted>"))
            .field("ca", &self.ca)
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
            ca: None,
        }
    }

    /// Pin the daemon's TLS certificate to the PEM file at `path`.
    ///
    /// The certificate joins the client's trust roots rather than replacing
    /// them, so a daemon that presents a publicly trusted certificate is
    /// still reachable.
    pub fn with_ca(mut self, path: impl Into<PathBuf>) -> Self {
        self.ca = Some(path.into());
        self
    }

    /// Read the configuration through `get`, so the precedence is testable
    /// without mutating process-global environment variables.
    pub fn from_lookup(get: impl Fn(&str) -> Option<String>) -> Option<Self> {
        let base_url = get(URL_ENV)?;
        let base_url = base_url.trim();
        if base_url.is_empty() {
            return None;
        }
        let mut config = Self::new(base_url, get(TOKEN_ENV));
        config.ca = get(CA_ENV)
            .map(|value| value.trim().to_string())
            .filter(|value| !value.is_empty())
            .map(PathBuf::from);
        Some(config)
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

    /// The PEM file holding the certificate to pin, when one is configured.
    pub fn ca_path(&self) -> Option<&Path> {
        self.ca.as_deref()
    }

    /// The bearer token, when one is configured.
    pub(crate) fn token(&self) -> Option<&str> {
        self.token.as_deref()
    }

    /// The URL of one of the daemon's routes.
    pub(crate) fn endpoint(&self, path: &str) -> String {
        format!("{}{path}", self.base_url)
    }
}
