//! MCP bridge over the browser lease broker.
//!
//! This crate owns the *tool logic*: every mutating operation passes the caller's
//! fencing token straight to the broker's on-disk [`substrate_browser::LeaseManager`],
//! so authority is enforced by the broker and not by this layer. The stdio server
//! binary (`src/bin/browser-broker-mcp.rs`) is a thin adapter over [`BrokerTools`].
//!
//! # One authority, never two
//!
//! The bridge resolves its state root with the same precedence `brokerd` uses -
//! `$SUBSTRATE_BROKER_ROOT`, else `$XDG_STATE_HOME/browser-broker`, else
//! `$HOME/.local/state/browser-broker` (see [`resolve_root_from`]). When both
//! processes agree on the root they share one on-disk lease store, so the MCP
//! server is never a competing authority.
//!
//! If `$BROKERD_URL` is set, the bridge instead acts on the *running* daemon
//! over its HTTP API ([`RemoteConfig`]). It never falls back to an in-process
//! broker in that mode: an unreachable daemon is an error, not an invitation to
//! mutate a different authority. Reads and mutations both go to the daemon
//! (`GET /v1/leases`, `GET /v1/sessions`, `POST /v1/leases`,
//! `POST /v1/leases/{id}/release`, `POST /v1/leases/reap`,
//! `POST /v1/profiles/purge`), so the daemon - not this process - owns the
//! lease, the browser and the guards.
//!
//! `$BROKERD_CA` names a PEM file holding the certificate to trust for the
//! daemon's TLS connection. It is added to the client's trust roots, so a
//! daemon with a self-signed certificate is reachable without installing
//! anything into the machine's trust store.
//!
//! # What is real, and what is not
//!
//! * `status`, `live`, `reap` are read-only or maintenance calls backed directly
//!   by [`Broker`].
//! * `acquire` and `release` are backed by [`Broker::acquire`] / [`Broker::release`]
//!   locally, and by the daemon's mutation routes when `$BROKERD_URL` is set.
//!   Acquiring launches a real browser; when no Chrome-family binary is present
//!   the authority returns its own error and this layer reports it verbatim.
//! * `release` validates the fencing token **before** touching anything. A stale
//!   token is refused and the lease stays in place (fail-closed).
//! * `purge` deletes the profile's data directory. It refuses without
//!   `confirm: true` and refuses while the profile is live or leased.

mod ca;
mod client;
mod config;
mod remote;
mod types;

use std::{
    collections::BTreeMap,
    ffi::OsString,
    path::PathBuf,
    sync::Arc,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

pub use client::{RemoteBroker, CA_ENV, TOKEN_ENV, URL_ENV};
pub use config::RemoteConfig;
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

/// Resolve the broker state root from `get`, which mirrors the process
/// environment.
///
/// The precedence is a contract shared with `brokerd`:
/// `SUBSTRATE_BROKER_ROOT`, else `XDG_STATE_HOME/browser-broker`, else
/// `HOME/.local/state/browser-broker`. Both crates test the same table, because
/// a divergence here is precisely how the MCP server becomes a second authority.
pub fn resolve_root_from(get: impl Fn(&str) -> Option<OsString>) -> PathBuf {
    if let Some(root) = get("SUBSTRATE_BROKER_ROOT") {
        return PathBuf::from(root);
    }
    if let Some(state) = get("XDG_STATE_HOME") {
        return PathBuf::from(state).join("browser-broker");
    }
    let home = get("HOME").unwrap_or_else(|| OsString::from("."));
    PathBuf::from(home)
        .join(".local")
        .join("state")
        .join("browser-broker")
}

/// Broker state root used when no override is given.
///
/// Identical to `brokerd`'s default, so the MCP server and the daemon share one
/// lease authority.
pub fn default_root() -> PathBuf {
    resolve_root_from(|name| std::env::var_os(name))
}

fn now_unix_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

/// Where this tool surface draws its authority from.
enum Backend {
    /// A broker owned by this process, on the resolved state root.
    Local(Broker),
    /// A running `brokerd` reached over HTTP.
    Remote(RemoteBroker),
}

/// Tool surface backed by one authority plus the sessions this process holds.
///
/// The broker is the only authority; `sessions` is just the set of handles this
/// process may still need to close. A lease that exists on disk but has no entry
/// here (for example after an MCP restart) can still be released, because
/// release re-validates against the lease store and revokes the record.
pub struct BrokerTools {
    backend: Backend,
    sessions: Mutex<BTreeMap<String, Acquired>>,
}

impl BrokerTools {
    /// Open the tool surface against a broker rooted at `root`.
    pub fn open(root: impl Into<PathBuf>) -> Result<Self> {
        Ok(Self {
            backend: Backend::Local(Broker::new(root)?),
            sessions: Mutex::new(BTreeMap::new()),
        })
    }

    /// Open against a running `brokerd` instead of an in-process broker.
    ///
    /// Reads and mutations are both served by the daemon, which owns the lease
    /// store, the browsers and the guards. Inventing a local authority instead
    /// would recreate the bug this crate exists to prevent.
    pub fn open_remote(config: RemoteConfig) -> Result<Self> {
        Ok(Self {
            backend: Backend::Remote(RemoteBroker::new(config)?),
            sessions: Mutex::new(BTreeMap::new()),
        })
    }

    /// Open against `$BROKERD_URL` when it is set, else [`default_root`].
    pub fn open_default() -> Result<Self> {
        match RemoteConfig::from_env() {
            Some(config) => Self::open_remote(config),
            None => Self::open(default_root()),
        }
    }

    /// Open against a broker whose lease authority uses an injected clock.
    ///
    /// Lets tests drive TTL expiry without sleeping.
    pub fn with_clock(
        root: impl Into<PathBuf>,
        clock: Arc<dyn substrate_browser::Clock>,
    ) -> Result<Self> {
        Ok(Self {
            backend: Backend::Local(Broker::with_clock(root, clock)?),
            sessions: Mutex::new(BTreeMap::new()),
        })
    }

    /// The in-process broker, when this instance owns one.
    ///
    /// `None` when the instance targets a running `brokerd`.
    pub fn broker(&self) -> Option<&Broker> {
        match &self.backend {
            Backend::Local(broker) => Some(broker),
            Backend::Remote(_) => None,
        }
    }

    /// Where this instance draws authority from, for startup diagnostics:
    /// the local state root, or `brokerd:<url>`.
    pub fn authority(&self) -> String {
        match &self.backend {
            Backend::Local(broker) => broker.root().display().to_string(),
            Backend::Remote(remote) => format!("brokerd:{}", remote.config().base_url()),
        }
    }

    /// Read-only snapshot: root, browser availability, sessions and leases.
    pub async fn status(&self) -> Result<BrokerStatus> {
        match &self.backend {
            Backend::Local(broker) => local_status(broker).await,
            Backend::Remote(remote) => {
                let now = now_unix_ms();
                let leases = remote.leases().await?;
                let live = remote.live().await?;
                Ok(BrokerStatus {
                    root: remote.config().base_url().to_string(),
                    brokerd: Some(remote.config().base_url().to_string()),
                    // The daemon host's browser inventory is not visible here.
                    browser_available: None,
                    live_sessions: live.len(),
                    active_leases: leases.iter().map(|lease| lease_info(lease, now)).collect(),
                })
            },
        }
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

        match &self.backend {
            Backend::Remote(remote) => {
                // The daemon launches and keeps the browser; this process gets a
                // descriptor, never a handle, so a dropped MCP session cannot
                // orphan or double-own a browser the daemon still holds.
                let acquired = remote
                    .acquire(
                        &params.principal,
                        &params.profile,
                        &session,
                        &holder,
                        ttl_ms,
                    )
                    .await?;
                Ok(AcquiredInfo {
                    lease_id: acquired.id,
                    fencing_token: acquired.fencing_token,
                    expires_at_unix_ms: acquired.expires_at_unix_ms,
                    generation: acquired.generation,
                    data_dir: acquired.data_dir,
                })
            },
            Backend::Local(broker) => {
                let scope = Scope::new(params.principal, params.profile, session)
                    .map_err(|e| BrokerError::State(BrowserError::Scope(e)))?;

                let acquired = broker
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
            },
        }
    }

    /// Release a lease after validating `fencing_token` against the lease store.
    ///
    /// The token check happens first and is the broker's own
    /// [`substrate_browser::LeaseManager::validate`], so an expired, revoked or
    /// superseded lease is refused and nothing is torn down.
    pub async fn release(&self, lease_id: &str, fencing_token: u64) -> Result<ReleaseOutcome> {
        let broker = match &self.backend {
            Backend::Remote(remote) => {
                // The daemon validates the fence with the same
                // `LeaseManager::validate` before it mutates anything, so a stale
                // token still tears nothing down - it is just checked there.
                let released = remote.release(lease_id, fencing_token).await?;
                return Ok(ReleaseOutcome {
                    released: released.released,
                    lease_id: lease_id.to_string(),
                    teardown: released.teardown,
                });
            },
            Backend::Local(broker) => broker,
        };

        // Fail-closed: never mutate before the broker's fence check passes.
        let lease = broker.leases().validate(lease_id, fencing_token)?;

        let acquired = self.sessions.lock().await.remove(lease_id);
        let teardown = match acquired {
            Some(acquired) => {
                // Release closes the browser first, then revokes and seals.
                broker.release(acquired).await?;
                "browser closed; lease revoked; generation sealed"
            },
            None => {
                // No local handle: the lease outlived a process restart, or the
                // browser was reaped. Revoking the record is the whole action.
                match broker.leases().revoke(&lease.id) {
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

    /// Live sessions held by the authority, after reaping expired ones.
    ///
    /// Local: sessions this process holds. Remote: sessions the daemon holds,
    /// which is the only set it can know about.
    pub async fn live(&self) -> Vec<LiveSessionInfo> {
        match &self.backend {
            Backend::Local(broker) => broker.live().await,
            // A failed read is reported as "nothing known", not as "nothing
            // live": callers that must not guess use `status`.
            Backend::Remote(remote) => remote.live().await.unwrap_or_default(),
        }
    }

    /// Reap expired or superseded sessions and report the counts.
    pub async fn reap(&self) -> Result<ReapOutcome> {
        let broker = match &self.backend {
            Backend::Remote(remote) => {
                let reaped = remote.reap().await?;
                return Ok(ReapOutcome {
                    reaped: reaped.reaped,
                    leases_reaped: reaped.leases_reaped,
                    live_sessions_after: reaped.live_sessions_after,
                });
            },
            Backend::Local(broker) => broker,
        };
        let reaped = broker.reap_expired().await;

        // Expired records authorise nothing, so sweeping them is safe: anything
        // that still needs authority re-validates and would fail closed.
        let leases_reaped = broker.leases().sweep_expired()?;

        // Drop local handles whose lease no longer validates, so a later
        // release reports `NoSession`/`UnknownLease` instead of pretending.
        let stale: Vec<String> = {
            let sessions = self.sessions.lock().await;
            sessions
                .iter()
                .filter(|(id, acquired)| {
                    broker
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
            live_sessions_after: broker.live().await.len(),
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
        // The daemon owns the guards when it is the authority: forwarding
        // `confirm` as sent means a false value is refused there, by the same
        // rule, instead of being quietly accepted by a second implementation.
        if let Backend::Remote(remote) = &self.backend {
            let purged = remote.purge(principal, profile, confirm).await?;
            return Ok(PurgeOutcome {
                purged: purged.purged,
                path: purged.path,
                existed: purged.existed,
            });
        }
        let Some(broker) = self.broker() else {
            return Err(BrokerError::State(BrowserError::Refused(
                "no authority to purge through".to_string(),
            )));
        };

        if !confirm {
            return Err(BrokerError::State(BrowserError::Refused(
                "purge is destructive: pass confirm: true to delete profile data".to_string(),
            )));
        }

        let scope = Scope::new(principal, profile, "default")
            .map_err(|e| BrokerError::State(BrowserError::Scope(e)))?;
        let key = scope.profile_key();

        // A live session's scope is `principal/profile/session`, so compare the
        // profile key as a prefix; equality would miss every live session.
        if broker
            .live()
            .await
            .iter()
            .any(|s| s.scope == key || s.scope.starts_with(&format!("{key}/")))
        {
            return Err(BrokerError::State(BrowserError::Refused(format!(
                "profile {key} has a live session; release it before purging"
            ))));
        }
        if let Some(lease) = broker.leases().active_for(principal, profile)? {
            return Err(BrokerError::State(BrowserError::Refused(format!(
                "profile {key} is leased by `{}` until {}; release it before purging",
                lease.holder, lease.expires_at_unix_ms
            ))));
        }

        let path = broker.profiles().profile_dir(principal, profile);
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

fn lease_info(lease: &Lease, now: u64) -> LeaseInfo {
    LeaseInfo {
        scope: lease.profile_key(),
        expired: lease.expires_at_unix_ms <= now,
        lease_id: lease.id.clone(),
        holder: lease.holder.clone(),
        fencing_token: lease.fencing_token,
        expires_at_unix_ms: lease.expires_at_unix_ms,
    }
}

async fn local_status(broker: &Broker) -> Result<BrokerStatus> {
    let now = now_unix_ms();
    let live_sessions = broker.live().await.len();
    let active_leases = broker
        .leases()
        .list()?
        .iter()
        .map(|lease| lease_info(lease, now))
        .collect();

    Ok(BrokerStatus {
        root: broker.root().display().to_string(),
        brokerd: None,
        browser_available: Some(browser_available()),
        live_sessions,
        active_leases,
    })
}

/// Convenience wrapper so binaries can share one `Arc<BrokerTools>`.
pub type SharedTools = Arc<BrokerTools>;
