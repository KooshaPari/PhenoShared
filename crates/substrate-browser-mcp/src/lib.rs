//! MCP bridge over the browser lease broker.
//!
//! This crate owns the *tool logic*: every mutating operation passes the caller's
//! fencing token straight to the broker's on-disk [`LeaseManager`], so authority
//! is enforced by the broker and not by this layer. The stdio server binary
//! (`src/bin/browser-broker-mcp.rs`) is a thin adapter over [`BrokerTools`].
//!
//! # What is real, and what is not
//!
//! * `status`, `live`, `reap` are read-only or maintenance calls backed directly
//!   by [`Broker`].
//! * `acquire` and `release` are backed by [`Broker::acquire`] / [`Broker::release`].
//!   Acquiring launches a real browser; when no Chrome-family binary is present
//!   the broker returns its own error and this layer reports it verbatim.
//! * `release` validates the fencing token **before** touching anything. A stale
//!   token is refused and the lease stays in place (fail-closed).
//! * `purge` deletes the profile's data directory. It refuses without
//!   `confirm: true` and refuses while the profile is live or leased.

mod types;

use std::{
    collections::BTreeMap,
    path::PathBuf,
    sync::Arc,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

pub use types::{
    kind_of, AcquireParams, AcquiredInfo, BrokerStatus, LeaseInfo, PurgeOutcome, PurgeParams,
    ReapOutcome, ReleaseOutcome, ReleaseParams, ToolError,
};

use substrate_browser::{BrowserError, Lease, Scope};
use substrate_browser_broker::{browser_available, Acquired, Broker, BrokerError, LiveSessionInfo};
use tokio::sync::Mutex;

/// Default lease lifetime for `broker_acquire`, in milliseconds.
pub const DEFAULT_TTL_MS: u64 = 60_000;

/// Result alias for the tool layer.
pub type Result<T> = std::result::Result<T, BrokerError>;

/// Broker state root used when no override is given.
///
/// Matches `brokerd` so the MCP server and the daemon share one lease authority:
/// `$SUBSTRATE_BROKER_ROOT`, else `$XDG_STATE_HOME/browser-broker`, else
/// `$HOME/.local/state/browser-broker`.
pub fn default_root() -> PathBuf {
    if let Some(root) = std::env::var_os("SUBSTRATE_BROKER_ROOT") {
        return PathBuf::from(root);
    }
    if let Some(state) = std::env::var_os("XDG_STATE_HOME") {
        return PathBuf::from(state).join("browser-broker");
    }
    let home = std::env::var_os("HOME").unwrap_or_else(|| ".".into());
    PathBuf::from(home)
        .join(".local")
        .join("state")
        .join("browser-broker")
}

fn now_unix_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

/// Tool surface backed by one [`Broker`] plus the sessions this process holds.
///
/// The broker is the only authority; `sessions` is just the set of handles this
/// process may still need to close. A lease that exists on disk but has no entry
/// here (for example after an MCP restart) can still be released, because
/// release re-validates against the lease store and revokes the record.
pub struct BrokerTools {
    broker: Broker,
    sessions: Mutex<BTreeMap<String, Acquired>>,
}

impl BrokerTools {
    /// Open the tool surface against a broker rooted at `root`.
    pub fn open(root: impl Into<PathBuf>) -> Result<Self> {
        Ok(Self {
            broker: Broker::new(root)?,
            sessions: Mutex::new(BTreeMap::new()),
        })
    }

    /// Open against [`default_root`].
    pub fn open_default() -> Result<Self> {
        Self::open(default_root())
    }

    /// Open against a broker whose lease authority uses an injected clock.
    ///
    /// Lets tests drive TTL expiry without sleeping.
    pub fn with_clock(
        root: impl Into<PathBuf>,
        clock: Arc<dyn substrate_browser::Clock>,
    ) -> Result<Self> {
        Ok(Self {
            broker: Broker::with_clock(root, clock)?,
            sessions: Mutex::new(BTreeMap::new()),
        })
    }

    /// The underlying broker. Exposed so callers can inspect state directly.
    pub fn broker(&self) -> &Broker {
        &self.broker
    }

    /// Root path shared with the daemon.
    pub fn root(&self) -> &std::path::Path {
        self.broker.root()
    }

    /// Read-only snapshot: root, browser availability, sessions and leases.
    pub async fn status(&self) -> Result<BrokerStatus> {
        let now = now_unix_ms();
        let live_sessions = self.broker.live().await.len();
        let active_leases = self
            .broker
            .leases()
            .list()?
            .into_iter()
            .map(|lease: Lease| LeaseInfo {
                scope: lease.profile_key(),
                expired: lease.expires_at_unix_ms <= now,
                lease_id: lease.id,
                holder: lease.holder,
                fencing_token: lease.fencing_token,
                expires_at_unix_ms: lease.expires_at_unix_ms,
            })
            .collect();

        Ok(BrokerStatus {
            root: self.broker.root().display().to_string(),
            browser_available: browser_available(),
            live_sessions,
            active_leases,
        })
    }

    /// Acquire an exclusive browser, keeping the handle in this process.
    pub async fn acquire(&self, params: AcquireParams) -> Result<AcquiredInfo> {
        let session = params.session.unwrap_or_else(|| "default".to_string());
        let holder = params
            .holder
            .unwrap_or_else(|| format!("mcp:{}", params.principal));
        let ttl_ms = params.ttl_ms.unwrap_or(DEFAULT_TTL_MS);
        if ttl_ms == 0 {
            return Err(BrokerError::State(BrowserError::Refused(
                "ttl_ms must be greater than zero".to_string(),
            )));
        }

        let scope = Scope::new(params.principal, params.profile, session)
            .map_err(|e| BrokerError::State(BrowserError::Scope(e)))?;

        let acquired = self
            .broker
            .acquire(&scope, holder, Duration::from_millis(ttl_ms))
            .await?;

        let info = AcquiredInfo {
            lease_id: acquired.lease.id.clone(),
            fencing_token: acquired.lease.fencing_token,
            expires_at_unix_ms: acquired.lease.expires_at_unix_ms,
            generation: acquired.generation,
            data_dir: acquired.data_dir.display().to_string(),
        };
        self.sessions
            .lock()
            .await
            .insert(info.lease_id.clone(), acquired);
        Ok(info)
    }

    /// Release a lease after validating `fencing_token` against the lease store.
    ///
    /// The token check happens first and is the broker's own
    /// [`substrate_browser::LeaseManager::validate`], so an expired, revoked or
    /// superseded lease is refused and nothing is torn down.
    pub async fn release(&self, lease_id: &str, fencing_token: u64) -> Result<ReleaseOutcome> {
        // Fail-closed: never mutate before the broker's fence check passes.
        let lease = self.broker.leases().validate(lease_id, fencing_token)?;

        let acquired = self.sessions.lock().await.remove(lease_id);
        let teardown = match acquired {
            Some(acquired) => {
                // Release closes the browser first, then revokes and seals.
                self.broker.release(acquired).await?;
                "browser closed; lease revoked; generation sealed"
            },
            None => {
                // No local handle: the lease outlived a process restart, or the
                // browser was reaped. Revoking the record is the whole action.
                match self.broker.leases().revoke(&lease.id) {
                    Ok(()) | Err(BrowserError::UnknownLease(_)) => {},
                    Err(err) => return Err(err.into()),
                }
                "no local session; lease record revoked"
            },
        };

        Ok(ReleaseOutcome {
            released: true,
            lease_id: lease_id.to_string(),
            teardown: teardown.to_string(),
        })
    }

    /// Live sessions this process holds (read-only; reaps expired ones first).
    pub async fn live(&self) -> Vec<LiveSessionInfo> {
        self.broker.live().await
    }

    /// Reap expired or superseded sessions and report the counts.
    pub async fn reap(&self) -> Result<ReapOutcome> {
        let reaped = self.broker.reap_expired().await;

        // Expired records authorise nothing, so sweeping them is safe: anything
        // that still needs authority re-validates and would fail closed.
        let leases_reaped = self.broker.leases().sweep_expired()?;

        // Drop local handles whose lease no longer validates, so a later
        // release reports `NoSession`/`UnknownLease` instead of pretending.
        let stale: Vec<String> = {
            let sessions = self.sessions.lock().await;
            sessions
                .iter()
                .filter(|(id, acquired)| {
                    self.broker
                        .leases()
                        .validate(id, acquired.lease.fencing_token)
                        .is_err()
                })
                .map(|(id, _)| id.clone())
                .collect()
        };
        if !stale.is_empty() {
            let mut sessions = self.sessions.lock().await;
            for id in stale {
                sessions.remove(&id);
            }
        }

        Ok(ReapOutcome {
            reaped,
            leases_reaped,
            live_sessions_after: self.broker.live().await.len(),
        })
    }

    /// Delete a profile's data directory. Destructive and fail-closed.
    ///
    /// Refused unless `confirm` is true, while a live session for the profile
    /// exists in this process, or while any unexpired lease exists on disk.
    pub async fn purge(
        &self,
        principal: &str,
        profile: &str,
        confirm: bool,
    ) -> Result<PurgeOutcome> {
        if !confirm {
            return Err(BrokerError::State(BrowserError::Refused(
                "purge is destructive: pass confirm: true to delete profile data".to_string(),
            )));
        }

        let scope = Scope::new(principal, profile, "default")
            .map_err(|e| BrokerError::State(BrowserError::Scope(e)))?;
        let key = scope.profile_key();

        if self.live().await.iter().any(|s| s.scope == key) {
            return Err(BrokerError::State(BrowserError::Refused(format!(
                "profile {key} has a live session; release it before purging"
            ))));
        }
        if let Some(lease) = self.broker.leases().active_for(principal, profile)? {
            return Err(BrokerError::State(BrowserError::Refused(format!(
                "profile {key} is leased by `{}` until {}; release it before purging",
                lease.holder, lease.expires_at_unix_ms
            ))));
        }

        let path = self.broker.profiles().profile_dir(principal, profile);
        if !path.exists() {
            return Ok(PurgeOutcome {
                purged: false,
                path: path.display().to_string(),
                existed: false,
            });
        }
        std::fs::remove_dir_all(&path).map_err(|e| BrokerError::State(e.into()))?;
        Ok(PurgeOutcome {
            purged: true,
            path: path.display().to_string(),
            existed: true,
        })
    }
}

/// Convenience wrapper so binaries can share one `Arc<BrokerTools>`.
pub type SharedTools = Arc<BrokerTools>;
