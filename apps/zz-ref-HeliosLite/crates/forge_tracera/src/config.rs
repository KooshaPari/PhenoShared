//! Configuration types for the Tracera sink.

use serde::{Deserialize, Serialize};
use std::time::Duration;

/// Authentication strategy used to sign requests to the Tracera endpoint.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum AuthMode {
    /// No authentication. Suitable for local development against an
    /// unauthenticated collector.
    #[default]
    None,

    /// Static bearer token sent in `Authorization: Bearer <token>`.
    Bearer {
        /// The token string.
        token: String,
    },

    /// HMAC-SHA256 signature. The hex digest of the request body is sent
    /// in `X-Tracera-Signature`. Suitable for webhook-style collectors.
    Hmac {
        /// Shared secret used as the HMAC key.
        secret: String,
        /// Header name to carry the signature in.
        #[serde(default = "default_hmac_header")]
        header: String,
    },
}

fn default_hmac_header() -> String {
    "X-Tracera-Signature".to_string()
}

impl AuthMode {
    /// Stable string identity used by the rotation overlap logic.
    ///
    /// Format: `"none"`, `"bearer:<token>"`, or `"hmac:<secret>"`. The
    /// `header` name on `Hmac` is intentionally excluded so header-name
    /// migrations don't trigger a second key rotation.
    ///
    /// Two [`AuthMode`]s are considered to have the same identity when
    /// their `kind` and (for HMAC) their `secret` / (for Bearer) their
    /// `token` match.
    pub fn identity(&self) -> String {
        match self {
            AuthMode::None => "none".to_string(),
            AuthMode::Bearer { token } => format!("bearer:{token}"),
            AuthMode::Hmac { secret, .. } => format!("hmac:{secret}"),
        }
    }

    /// Returns true when this auth mode carries a credential that should
    /// be redacted in logs / debug output.
    pub fn has_secret(&self) -> bool {
        matches!(self, AuthMode::Bearer { .. } | AuthMode::Hmac { .. })
    }

    /// Validate the auth mode — rejects empty tokens / secrets.
    pub fn validate(&self) -> Result<(), String> {
        match self {
            AuthMode::None => Ok(()),
            AuthMode::Bearer { token } if token.is_empty() => {
                Err("bearer token is empty".to_string())
            }
            AuthMode::Bearer { .. } => Ok(()),
            AuthMode::Hmac { secret, .. } if secret.is_empty() => {
                Err("hmac secret is empty".to_string())
            }
            AuthMode::Hmac { header, .. } if header.is_empty() => {
                Err("hmac header name is empty".to_string())
            }
            AuthMode::Hmac { .. } => Ok(()),
        }
    }
}

/// Top-level sink configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SinkConfig {
    /// HTTP endpoint accepting `POST { "events": [...] }`.
    pub endpoint: String,

    /// Authentication mode.
    #[serde(default)]
    pub auth: AuthMode,

    /// Maximum number of events buffered in memory before backpressure.
    #[serde(default = "default_capacity")]
    pub capacity: usize,

    /// When true, `submit` blocks until there is room in the buffer;
    /// otherwise it returns [`SinkError::StoreFull`](crate::SinkError::StoreFull).
    #[serde(default)]
    pub block_on_full: bool,

    /// Maximum events sent per HTTP batch.
    #[serde(default = "default_batch_size")]
    pub batch_size: usize,

    /// Maximum retry attempts for transient failures (5xx, 429, network).
    #[serde(default = "default_max_retries")]
    pub max_retries: u32,

    /// Initial backoff between retries. Doubled each attempt up to
    /// `max_backoff`.
    #[serde(default = "default_initial_backoff", with = "humantime_serde_compat")]
    pub initial_backoff: Duration,

    /// Upper bound on the exponential backoff.
    #[serde(default = "default_max_backoff", with = "humantime_serde_compat")]
    pub max_backoff: Duration,

    /// HTTP request timeout.
    #[serde(default = "default_request_timeout", with = "humantime_serde_compat")]
    pub request_timeout: Duration,

    /// Source identifier stamped on every event. Defaults to "forgecode".
    #[serde(default = "default_source")]
    pub source: String,

    /// When true, outbound batches are gzipped and sent with
    /// `Content-Encoding: gzip`.
    ///
    /// Default: true. Disable for endpoints that cannot decode gzip, or
    /// for tiny batches where the CPU cost outweighs the network savings.
    #[serde(default = "default_compression_enabled")]
    pub compression_enabled: bool,

    /// Duration of the auth overlap window in milliseconds.
    ///
    /// When [`TraceraSink::rotate_auth`](crate::TraceraSink::rotate_auth)
    /// is called, the previous auth mode remains active (requests are
    /// signed with both the new and the old credentials) for this many
    /// milliseconds. After the window elapses the previous mode is
    /// dropped — collectors must be ready to accept only the new
    /// credential by then.
    ///
    /// Set to `0` to disable overlap (the previous mode is dropped
    /// immediately on rotation).
    #[serde(
        default = "default_auth_overlap_window_ms",
        with = "humantime_serde_compat"
    )]
    pub auth_overlap_window_ms: Duration,
}

fn default_capacity() -> usize {
    4096
}

fn default_batch_size() -> usize {
    64
}

fn default_max_retries() -> u32 {
    5
}

fn default_initial_backoff() -> Duration {
    Duration::from_millis(200)
}

fn default_max_backoff() -> Duration {
    Duration::from_secs(30)
}

fn default_request_timeout() -> Duration {
    Duration::from_secs(10)
}

fn default_source() -> String {
    "forgecode".to_string()
}

fn default_compression_enabled() -> bool {
    true
}

fn default_auth_overlap_window_ms() -> Duration {
    Duration::from_millis(60_000)
}

impl Default for SinkConfig {
    fn default() -> Self {
        Self {
            endpoint: "http://127.0.0.1:7700/v1/events".to_string(),
            auth: AuthMode::None,
            capacity: default_capacity(),
            block_on_full: false,
            batch_size: default_batch_size(),
            max_retries: default_max_retries(),
            initial_backoff: default_initial_backoff(),
            max_backoff: default_max_backoff(),
            request_timeout: default_request_timeout(),
            source: default_source(),
            compression_enabled: default_compression_enabled(),
            auth_overlap_window_ms: default_auth_overlap_window_ms(),
        }
    }
}

impl SinkConfig {
    /// Validate this configuration; returns the first error found.
    pub fn validate(&self) -> Result<(), String> {
        if self.endpoint.trim().is_empty() {
            return Err("endpoint is empty".to_string());
        }
        // require absolute URL with http or https scheme
        let url = url::Url::parse(&self.endpoint)
            .map_err(|e| format!("endpoint is not a valid URL: {e}"))?;
        match url.scheme() {
            "http" | "https" => {}
            other => {
                return Err(format!(
                    "endpoint scheme must be http or https, got {other}"
                ));
            }
        }
        if self.batch_size == 0 {
            return Err("batch_size must be > 0".to_string());
        }
        if self.capacity == 0 {
            return Err("capacity must be > 0".to_string());
        }
        if self.max_retries == 0 {
            return Err("max_retries must be > 0".to_string());
        }
        Ok(())
    }
}

/// Tiny shim so we can serialize [`Duration`] as seconds without dragging
/// in the `humantime_serde` crate just for this. The config type still
/// works when serialized to JSON: durations are encoded as integer seconds.
pub mod humantime_serde_compat {
    use serde::{Deserialize, Deserializer, Serializer};
    use std::time::Duration;

    /// Serialize a `Duration` as integer milliseconds.
    pub fn serialize<S: Serializer>(d: &Duration, s: S) -> Result<S::Ok, S::Error> {
        let ms = d.as_millis() as u64;
        s.serialize_u64(ms)
    }

    /// Deserialize a `Duration` from integer milliseconds.
    pub fn deserialize<'de, D: Deserializer<'de>>(d: D) -> Result<Duration, D::Error> {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum Ms {
            U64(u64),
            I64(i64),
        }
        let ms = match Ms::deserialize(d)? {
            Ms::U64(v) => v,
            Ms::I64(v) => v.max(0) as u64,
        };
        Ok(Duration::from_millis(ms))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn auth_mode_validate_catches_empty_token() {
        let bad = AuthMode::Bearer { token: String::new() };
        assert!(bad.validate().is_err());
    }

    #[test]
    fn auth_mode_validate_accepts_bearer() {
        let ok = AuthMode::Bearer { token: "abc".into() };
        assert!(ok.validate().is_ok());
    }

    #[test]
    fn auth_mode_validate_catches_empty_secret() {
        let bad = AuthMode::Hmac { secret: String::new(), header: "X-Sig".into() };
        assert!(bad.validate().is_err());
    }

    #[test]
    fn auth_mode_validate_catches_empty_header() {
        let bad = AuthMode::Hmac { secret: "s".into(), header: String::new() };
        assert!(bad.validate().is_err());
    }

    #[test]
    fn auth_mode_has_secret() {
        assert!(!AuthMode::None.has_secret());
        assert!(AuthMode::Bearer { token: "x".into() }.has_secret());
        assert!(AuthMode::Hmac { secret: "x".into(), header: "X".into() }.has_secret());
    }

    #[test]
    fn auth_mode_identity_is_stable() {
        let a = AuthMode::Hmac { secret: "k1".into(), header: "X-A".into() };
        let b = AuthMode::Hmac { secret: "k1".into(), header: "X-B".into() };
        // header rename must NOT change identity.
        assert_eq!(a.identity(), b.identity());
        let c = AuthMode::Hmac { secret: "k2".into(), header: "X-A".into() };
        assert_ne!(a.identity(), c.identity());
        assert_eq!(AuthMode::None.identity(), "none");
        assert_eq!(
            AuthMode::Bearer { token: "tok".into() }.identity(),
            "bearer:tok"
        );
    }

    #[test]
    fn config_default_validates() {
        SinkConfig::default()
            .validate()
            .expect("default must validate");
    }

    #[test]
    fn config_default_compression_enabled() {
        assert!(SinkConfig::default().compression_enabled);
        assert_eq!(
            SinkConfig::default().auth_overlap_window_ms,
            Duration::from_millis(60_000)
        );
    }

    #[test]
    fn config_rejects_empty_endpoint() {
        let c = SinkConfig { endpoint: String::new(), ..SinkConfig::default() };
        assert!(c.validate().is_err());
    }

    #[test]
    fn config_rejects_bad_scheme() {
        let c = SinkConfig {
            endpoint: "ftp://example.com".to_string(),
            ..SinkConfig::default()
        };
        assert!(c.validate().is_err());
    }

    #[test]
    fn config_rejects_zero_batch_size() {
        let c = SinkConfig { batch_size: 0, ..SinkConfig::default() };
        assert!(c.validate().is_err());
    }

    #[test]
    fn config_accepts_https_endpoint() {
        let c = SinkConfig {
            endpoint: "https://example.com/v1/events".to_string(),
            ..SinkConfig::default()
        };
        assert!(c.validate().is_ok());
    }
}
