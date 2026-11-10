//! `substrate-browser-broker` - the one place that ties a caller, a profile
//! generation, a lease and a live browser together.
//!
//! # Why a broker
//!
//! Profiles and leases are only useful if something enforces them at the moment
//! a browser is started. [`Broker::acquire`] does exactly that, in this order:
//!
//! 1. ensure the profile exists and resolve its active **generation**,
//! 2. **grant** an exclusive lease on that profile,
//! 3. publish the live session under its lease id.
//!
//! Acquiring is deliberately cheap: the browser that will use that generation is
//! launched on the session's **first action**, not here. A Chrome start takes
//! tens of seconds on a loaded host, and doing it inside acquire made a lease
//! grant as expensive as a browser launch (and pushed the HTTP acquire call past
//! any sane client timeout). The invariant that a failed launch must not hold
//! the profile is preserved inside [`BrowserHandle`]: a launch that fails
//! revokes the lease.
//!
//! Any step failing rolls back the earlier ones. [`Broker::release`] reverses it
//! in the opposite direction: close the browser (which does nothing when it was never
//! launched), revoke the lease, seal the generation so it may be forked.
//!
//! Because the live session is keyed by lease id, an observer can ask for *that*
//! lease's browser rather than guessing which process is which.
//!
//! # Fail-closed authority
//!
//! [`BrowserHandle`] is cloneable, so holding one does not authorise anything by
//! itself. Every action re-validates the lease against the on-disk
//! [`LeaseManager`] (existence, TTL and fencing token), which is the
//! cross-process authority. Expired, revoked or superseded sessions are purged
//! and their browser closed when this process is the last owner. Listing
//! [`Broker::live`] is a hint, not an authorisation: act through
//! [`Broker::browser`] or [`Broker::screenshot`], which re-check.
//!
//! # Lifecycle order
//!
//! Release stops the browser **first**, then revokes the lease, then seals the
//! generation. If the browser cannot be stopped the lease is left in place and
//! the generation is not sealed, so the profile cannot be handed to a new
//! holder while an old browser is still running. Every clone of the handle is
//! also revoked in-process at that moment, so a handle kept by a caller cannot
//! touch the browser after release even if its lease record outlived the call.
//!
//! Remaining limitation: the broker can only stop browsers **it** launched. A
//! browser left running by a crashed broker process is invisible to this
//! process; the on-disk lease (advisory lock plus fencing token) is the only
//! cross-process guard.

#![deny(missing_docs)]

mod handle;
mod lease_guard;
mod viewer;

pub use viewer::{router, router_with, serve, ViewerConfig};

// Re-exported so callers can build scopes and read leases without taking a
// second direct dependency.
pub use handle::BrowserHandle;
pub(crate) use handle::LaunchSpec;
pub use lease_guard::LeaseGuard;
pub use substrate_browser::{Clock, Lease, Scope};

/// True when a Chrome-family binary is available for the broker to launch.
pub fn browser_available() -> bool {
    substrate_browser_cdp::chrome_binary().is_ok()
}

use std::{
    collections::BTreeMap,
    path::{Path, PathBuf},
    sync::Arc,
    time::Duration,
};

use substrate_browser::{LeaseManager, ProfileStore};
use substrate_browser_cdp::CdpError;
use thiserror::Error;
use tokio::sync::RwLock;

/// Errors produced by the broker.
#[derive(Debug, Error)]
pub enum BrokerError {
    /// Profile or lease state failed.
    #[error(transparent)]
    State(#[from] substrate_browser::BrowserError),

    /// Browser launch or control failed.
    #[error(transparent)]
    Browser(#[from] CdpError),

    /// No live session exists for that lease.
    #[error("no live browser session for lease {0}")]
    NoSession(String),

    /// The caller tried to release something it does not hold.
    #[error("lease {lease} is held by `{holder}`, not by this caller")]
    NotHolder {
        /// Lease identifier.
        lease: String,
        /// Recorded holder.
        holder: String,
    },

    /// The lease is still valid on disk, but its browser was already stopped
    /// here (released, expired, superseded, or shut down).
    #[error("browser for lease {lease} is no longer running")]
    Released {
        /// Lease identifier.
        lease: String,
    },

    /// The profile already has a live browser in this process.
    #[error("profile {scope} is already held by lease {lease}")]
    ProfileBusy {
        /// Principal and profile.
        scope: String,
        /// Lease currently holding it.
        lease: String,
    },

    /// The browser was busy with another action for longer than the hold limit.
    ///
    /// Reported instead of waiting forever, so a stuck DevTools call cannot
    /// wedge release, reaping or the next acquire.
    #[error("browser for lease {lease} did not become available in time")]
    Busy {
        /// Lease identifier.
        lease: String,
    },
}

/// Result alias for this crate.
pub type Result<T> = std::result::Result<T, BrokerError>;

/// A live, lease-guarded browser.
pub struct Acquired {
    /// The lease authorising use of the profile.
    pub lease: Lease,
    /// Profile generation in use.
    pub generation: u64,
    /// Browser user data directory for that generation.
    pub data_dir: PathBuf,
    /// The live browser.
    pub browser: BrowserHandle,
}

impl std::fmt::Debug for Acquired {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Acquired")
            .field("lease", &self.lease.id)
            .field("generation", &self.generation)
            .finish_non_exhaustive()
    }
}

struct LiveSession {
    scope: Scope,
    generation: u64,
    holder: String,
    expires_at_unix_ms: u64,
    guard: LeaseGuard,
    browser: BrowserHandle,
}

/// Summary of one live session, safe to serialize to an observer.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct LiveSessionInfo {
    /// Lease identifier.
    pub lease_id: String,
    /// Holder label.
    pub holder: String,
    /// Principal and profile.
    pub scope: String,
    /// Profile generation.
    pub generation: u64,
    /// Expiry, milliseconds since the Unix epoch.
    pub expires_at_unix_ms: u64,
}

/// Profiles, leases and live browsers under one authority.
pub struct Broker {
    root: PathBuf,
    store: ProfileStore,
    leases: Arc<LeaseManager>,
    sessions: RwLock<BTreeMap<String, LiveSession>>,
    headless: bool,
}

impl Broker {
    /// Open a broker rooted at `root`.
    ///
    /// Creates `profiles/` and `leases/` beneath it.
    pub fn new(root: impl Into<PathBuf>) -> Result<Self> {
        Self::with_clock(root, Arc::new(substrate_browser::SystemClock))
    }

    /// Open a broker whose lease authority uses an injected clock.
    ///
    /// Lets callers (and tests) observe TTL expiry without sleeping.
    pub fn with_clock(root: impl Into<PathBuf>, clock: Arc<dyn Clock>) -> Result<Self> {
        let root = root.into();
        let leases = Arc::new(LeaseManager::with_clock(root.join("leases"), clock)?);
        // ProfileStore creates its own `profiles/` child inside the root it is
        // given, so pass the root itself. Passing root/profiles produced the
        // doubled `profiles/profiles/` layout.
        let store = ProfileStore::with_gate(root.clone(), leases.clone())?;
        Ok(Self {
            root,
            store,
            leases,
            sessions: RwLock::new(BTreeMap::new()),
            headless: true,
        })
    }

    /// Run browsers with a window.
    pub fn headed(mut self) -> Self {
        self.headless = false;
        self
    }

    /// Root directory.
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// The profile store.
    pub fn profiles(&self) -> &ProfileStore {
        &self.store
    }

    /// The lease authority.
    pub fn leases(&self) -> &LeaseManager {
        &self.leases
    }

    /// Acquire an exclusive browser for `scope`.
    pub async fn acquire(
        &self,
        scope: &Scope,
        holder: impl Into<String>,
        ttl: Duration,
    ) -> Result<Acquired> {
        let holder = holder.into();

        // Close anything already expired in this process before deciding what
        // the profile is free to do next.
        self.reap_expired().await;

        // One live browser per profile per process: a second launch against the
        // same user data directory would corrupt it, so refuse while a session
        // for this profile still exists (even one whose lease is still valid
        // but whose handle has not been released yet).
        if let Some(lease) = self
            .sessions
            .read()
            .await
            .iter()
            .find(|(_, session)| session.scope.profile_key() == scope.profile_key())
            .map(|(lease_id, _)| lease_id.clone())
        {
            return Err(BrokerError::ProfileBusy {
                scope: scope.profile_key(),
                lease,
            });
        }

        let generation = self.store.ensure(scope.principal(), scope.profile())?;
        // A broker that crashed mid-hold leaves a record that would block this
        // profile until its TTL. Reap owners that no longer exist first.
        let _ = self.leases.reap_dead();
        let lease = self.leases.grant(scope, holder.clone(), ttl)?;
        let guard = LeaseGuard::new(self.leases.clone(), &lease);

        // Deny a lease that is already unusable (expired on the shared clock)
        // before any browser exists.
        if let Err(err) = guard.check() {
            let _ = self.leases.revoke(&lease.id);
            return Err(err);
        }

        let data_dir = self
            .store
            .data_dir(scope.principal(), scope.profile(), generation);

        // No browser is launched here. The handle starts one on its first action
        // and owns the two invariants that used to hang off the eager launch: a
        // failed launch revokes this lease, and a browser is never handed out
        // under a lease that died while it was starting.
        let browser = BrowserHandle::new(
            LaunchSpec {
                data_dir: data_dir.clone(),
                headless: self.headless,
            },
            guard.clone(),
        );
        self.sessions.write().await.insert(
            lease.id.clone(),
            LiveSession {
                scope: scope.clone(),
                generation,
                holder,
                expires_at_unix_ms: lease.expires_at_unix_ms,
                guard,
                browser: browser.clone(),
            },
        );

        Ok(Acquired {
            lease,
            generation,
            data_dir,
            browser,
        })
    }

    /// Close the browser, revoke the lease and seal the generation.
    pub async fn release(&self, acquired: Acquired) -> Result<()> {
        self.release_inner(acquired, None).await
    }

    /// Release only if `holder` still owns the lease.
    pub async fn release_as(&self, acquired: Acquired, holder: &str) -> Result<()> {
        self.release_inner(acquired, Some(holder.to_string())).await
    }

    async fn release_inner(&self, acquired: Acquired, holder: Option<String>) -> Result<()> {
        let lease_id = acquired.lease.id.clone();

        // Authorise before mutating anything: a non-holder must not be able to
        // tear down somebody else's session as a side effect of a failed call.
        if let Some(holder) = holder {
            if holder != acquired.lease.holder {
                return Err(BrokerError::NotHolder {
                    lease: lease_id,
                    holder: acquired.lease.holder.clone(),
                });
            }
        }

        let Acquired {
            browser,
            lease,
            generation,
            ..
        } = acquired;

        // Close the browser first: the generation may only be sealed once no
        // live reader exists. A failure here aborts the release, leaving the
        // lease and generation in place so the profile cannot be reissued while
        // the old browser is still running.
        browser.shutdown().await?;
        self.sessions.write().await.remove(&lease.id);

        // An already-expired or already-revoked lease counts as revoked; only a
        // real storage failure is reported. Sealing still runs either way.
        let revoked = match self.leases.revoke(&lease.id) {
            Ok(()) => Ok(()),
            Err(substrate_browser::BrowserError::UnknownLease(_)) => Ok(()),
            Err(err) => Err(err),
        };
        let sealed = self
            .store
            .seal(&lease.principal, &lease.profile, generation);
        revoked?;
        sealed?;
        Ok(())
    }

    /// Every session whose lease is still valid.
    ///
    /// Purges expired, revoked and superseded sessions on the way through, so a
    /// stale entry is never advertised as live. The listing is a hint: actions
    /// re-validate via [`Broker::authorize`].
    pub async fn live(&self) -> Vec<LiveSessionInfo> {
        self.reap_expired().await;
        self.sessions
            .read()
            .await
            .iter()
            .map(|(lease_id, session)| LiveSessionInfo {
                lease_id: lease_id.clone(),
                holder: session.holder.clone(),
                scope: session.scope.to_string(),
                generation: session.generation,
                expires_at_unix_ms: session.expires_at_unix_ms,
            })
            .collect()
    }

    /// Drop sessions whose lease no longer validates, closing each browser when
    /// this process is the last owner. Returns how many were reaped.
    pub async fn reap_expired(&self) -> usize {
        // Dead owners are cheap to clear and are not reflected in `sessions`.
        let _ = self.leases.reap_dead();
        let stale: Vec<(String, BrowserHandle)> = {
            let sessions = self.sessions.read().await;
            sessions
                .iter()
                .filter(|(_, session)| session.guard.check().is_err())
                .map(|(id, session)| (id.clone(), session.browser.clone()))
                .collect()
        };
        let reaped = stale.len();
        for (lease_id, browser) in stale {
            self.purge(&lease_id, Some(browser)).await;
        }
        reaped
    }

    /// Authorise `lease_id`, returning its current lease record.
    ///
    /// A session whose lease expired, was revoked, or was superseded by a later
    /// grant is purged and the error returned.
    pub async fn authorize(&self, lease_id: &str) -> Result<Lease> {
        let session = {
            let sessions = self.sessions.read().await;
            sessions
                .get(lease_id)
                .map(|session| (session.guard.clone(), session.browser.clone()))
        };
        let Some((guard, browser)) = session else {
            return Err(BrokerError::NoSession(lease_id.to_string()));
        };
        match guard.check() {
            Ok(lease) => Ok(lease),
            Err(err) => {
                // Do not revoke: a superseded profile may now belong to a newer
                // holder, and an expired lease is already inert.
                self.purge(lease_id, Some(browser)).await;
                Err(err)
            },
        }
    }

    /// The browser for a specific lease.
    pub async fn browser(&self, lease_id: &str) -> Result<BrowserHandle> {
        self.authorize(lease_id).await?;
        self.sessions
            .read()
            .await
            .get(lease_id)
            .map(|session| session.browser.clone())
            .ok_or_else(|| BrokerError::NoSession(lease_id.to_string()))
    }

    /// Capture the page of the browser holding `lease_id`.
    pub async fn screenshot(&self, lease_id: &str) -> Result<Vec<u8>> {
        let browser = self.browser(lease_id).await?;
        browser.screenshot().await
    }

    /// Remove a session and close its browser when it is the last owner.
    async fn purge(&self, lease_id: &str, browser: Option<BrowserHandle>) {
        if let Some(browser) = browser {
            // Stops the browser even when callers still hold cloned handles;
            // a failed stop leaves the browser running, so the session is kept
            // rather than advertised as free.
            if browser.shutdown().await.is_err() {
                return;
            }
        }
        self.sessions.write().await.remove(lease_id);
    }
}
