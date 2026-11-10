//! The shapes a running `brokerd` answers with.
//!
//! These belong to the daemon's HTTP API rather than to the MCP tool
//! surface, so they live apart from the tool types: the client decodes them,
//! and the tool layer turns them into the answers its own callers see.

use serde::Deserialize;

/// The daemon's answer to `POST /v1/leases`.
#[derive(Debug, Clone, Deserialize)]
pub struct RemoteAcquired {
    /// Lease identifier the daemon granted.
    pub id: String,
    /// Fencing token that must accompany every later mutation.
    pub fencing_token: u64,
    /// Lease expiry, milliseconds since the Unix epoch.
    pub expires_at_unix_ms: u64,
    /// Profile generation the daemon launched.
    pub generation: u64,
    /// Browser user data directory, on the daemon's disk.
    pub data_dir: String,
}

/// The daemon's answer to `POST /v1/leases/{id}/release`.
#[derive(Debug, Clone, Deserialize)]
pub struct RemoteReleased {
    /// True; refusals never arrive as a success body.
    pub released: bool,
    /// What the daemon actually tore down.
    pub teardown: String,
}

/// The daemon's answer to `POST /v1/leases/reap`.
#[derive(Debug, Clone, Deserialize)]
pub struct RemoteReaped {
    /// Sessions reaped in the daemon.
    pub reaped: usize,
    /// Expired lease records swept from the shared store.
    pub leases_reaped: usize,
    /// Live sessions remaining afterwards.
    pub live_sessions_after: usize,
}

/// The daemon's answer to `POST /v1/profiles/purge`.
#[derive(Debug, Clone, Deserialize)]
pub struct RemotePurged {
    /// True when the profile directory was removed.
    pub purged: bool,
    /// Profile directory that was (or would have been) removed.
    pub path: String,
    /// False when the profile had no data on disk.
    pub existed: bool,
}
