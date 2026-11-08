//! Wire types shared by the MCP tools and their callers.
//!
//! Parameter structs derive [`schemars::JsonSchema`] so the MCP layer can
//! publish accurate input schemas. Response structs are serialized to JSON text
//! content, so they only need `Serialize`.

use serde::{Deserialize, Serialize};
use substrate_browser::BrowserError;
use substrate_browser_broker::BrokerError;

/// Parameters for `broker_acquire`.
#[derive(Debug, Clone, Deserialize, schemars::JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct AcquireParams {
    /// Principal (agent identity or tenant) that owns the profile.
    pub principal: String,
    /// Named browser profile to lease.
    pub profile: String,
    /// Logical session name; defaults to `default`.
    #[serde(default)]
    pub session: Option<String>,
    /// Human-readable holder label; defaults to a generated `mcp:<principal>`.
    #[serde(default)]
    pub holder: Option<String>,
    /// Lease lifetime in milliseconds; defaults to 60000.
    #[serde(default)]
    pub ttl_ms: Option<u64>,
}

/// Parameters for `broker_release`.
#[derive(Debug, Clone, Deserialize, schemars::JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ReleaseParams {
    /// Lease identifier returned by `broker_acquire`.
    pub lease_id: String,
    /// Fencing token returned by `broker_acquire`.
    ///
    /// A stale token is refused; the lease is never released on a bad token.
    pub fencing_token: u64,
}

/// Parameters for `broker_purge`.
#[derive(Debug, Clone, Deserialize, schemars::JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct PurgeParams {
    /// Principal that owns the profile.
    pub principal: String,
    /// Profile whose data directory should be deleted.
    pub profile: String,
    /// Must be `true`. Destructive: deletes every generation of the profile.
    pub confirm: bool,
}

/// One active lease, as reported by `broker_status`.
#[derive(Debug, Clone, Serialize)]
pub struct LeaseInfo {
    /// Lease identifier.
    pub lease_id: String,
    /// Recorded holder label.
    pub holder: String,
    /// `principal/profile` exclusivity key.
    pub scope: String,
    /// Monotonic per-profile fencing token.
    pub fencing_token: u64,
    /// Expiry, milliseconds since the Unix epoch.
    pub expires_at_unix_ms: u64,
    /// True when the expiry has already passed.
    pub expired: bool,
}

/// Result of `broker_status`.
#[derive(Debug, Clone, Serialize)]
pub struct BrokerStatus {
    /// Broker state root.
    pub root: String,
    /// Whether a Chrome-family binary exists for the broker to launch.
    pub browser_available: bool,
    /// Number of live sessions held by *this* process.
    pub live_sessions: usize,
    /// Every lease record on disk (expired ones flagged, not hidden).
    pub active_leases: Vec<LeaseInfo>,
}

/// Result of `broker_acquire`.
#[derive(Debug, Clone, Serialize)]
pub struct AcquiredInfo {
    /// Lease identifier.
    pub lease_id: String,
    /// Fencing token that must accompany every later mutation.
    pub fencing_token: u64,
    /// Lease expiry, milliseconds since the Unix epoch.
    pub expires_at_unix_ms: u64,
    /// Profile generation in use.
    pub generation: u64,
    /// Browser user data directory for that generation.
    pub data_dir: String,
}

/// Result of `broker_release`.
#[derive(Debug, Clone, Serialize)]
pub struct ReleaseOutcome {
    /// Always `true` when returned; refusals surface as [`ToolError`].
    pub released: bool,
    /// Lease that was released.
    pub lease_id: String,
    /// What the broker actually tore down.
    pub teardown: String,
}

/// Result of `broker_reap`.
#[derive(Debug, Clone, Serialize)]
pub struct ReapOutcome {
    /// Sessions reaped by the broker in this process.
    pub reaped: usize,
    /// Expired lease records removed from the on-disk store.
    pub leases_reaped: usize,
    /// Live sessions remaining afterwards.
    pub live_sessions_after: usize,
}

/// Result of `broker_purge`.
#[derive(Debug, Clone, Serialize)]
pub struct PurgeOutcome {
    /// True when the profile directory was removed by this call.
    pub purged: bool,
    /// Profile directory that was (or would have been) removed.
    pub path: String,
    /// False when the profile had no data on disk.
    pub existed: bool,
}

/// A broker failure, rendered for the agent instead of a transport error.
#[derive(Debug, Clone, Serialize)]
pub struct ToolError {
    /// `BrokerError` variant name, e.g. `StaleFence` or `Refused`.
    pub kind: &'static str,
    /// Full `Display` text from the broker.
    pub message: String,
}

impl ToolError {
    /// Classify a broker error by its variant.
    pub fn from_broker(err: &BrokerError) -> Self {
        Self {
            kind: kind_of(err),
            message: err.to_string(),
        }
    }
}

/// Variant name for a [`BrokerError`].
pub fn kind_of(err: &BrokerError) -> &'static str {
    match err {
        BrokerError::State(inner) => match inner {
            BrowserError::Scope(_) => "Scope",
            BrowserError::UnknownGeneration { .. } => "UnknownGeneration",
            BrowserError::PromotionConflict { .. } => "PromotionConflict",
            BrowserError::Refused(_) => "Refused",
            BrowserError::UnknownLease(_) => "UnknownLease",
            BrowserError::LeaseUnusable { .. } => "LeaseUnusable",
            BrowserError::StaleFence { .. } => "StaleFence",
            BrowserError::Io(_) => "Io",
        },
        BrokerError::Browser(_) => "Browser",
        BrokerError::NoSession(_) => "NoSession",
        BrokerError::NotHolder { .. } => "NotHolder",
        BrokerError::Released { .. } => "Released",
        BrokerError::ProfileBusy { .. } => "ProfileBusy",
        BrokerError::Busy { .. } => "Busy",
    }
}
