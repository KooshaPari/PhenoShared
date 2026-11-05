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
//! 3. launch a browser whose user data directory is that generation,
//! 4. publish the live session under its lease id.
//!
//! Any step failing rolls back the earlier ones. [`Broker::release`] reverses it
//! in the opposite direction: close the browser, revoke the lease, seal the
//! generation so it may be forked.
//!
//! Because the live session is keyed by lease id, an observer can ask for *that*
//! lease's browser rather than guessing which process is which.

#![deny(missing_docs)]

mod viewer;

pub use viewer::{router, serve, ViewerConfig};

// Re-exported so callers can build scopes and read leases without taking a
// second direct dependency.
pub use substrate_browser::{Lease, Scope};

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
use substrate_browser_cdp::{CdpError, CdpProvider};
use thiserror::Error;
use tokio::sync::{Mutex, RwLock};

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
}

/// Result alias for this crate.
pub type Result<T> = std::result::Result<T, BrokerError>;

/// A handle to one live browser, shared between the caller and the viewer.
#[derive(Clone)]
pub struct BrowserHandle(Arc<Mutex<CdpProvider>>);

impl BrowserHandle {
    /// Lock the browser for exclusive use.
    pub async fn lock(&self) -> tokio::sync::MutexGuard<'_, CdpProvider> {
        self.0.lock().await
    }

    /// Operating system process id of the backing browser.
    pub async fn pid(&self) -> Option<u32> {
        self.0.lock().await.pid()
    }
}

impl std::fmt::Debug for BrowserHandle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("BrowserHandle").finish_non_exhaustive()
    }
}

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
        let root = root.into();
        let leases = Arc::new(LeaseManager::new(root.join("leases"))?);
        let store = ProfileStore::with_gate(root.join("profiles"), leases.clone())?;
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
        let generation = self.store.ensure(scope.principal(), scope.profile())?;
        let lease = self.leases.grant(scope, holder.clone(), ttl)?;

        let data_dir = self
            .store
            .data_dir(scope.principal(), scope.profile(), generation);
        let provider = match CdpProvider::launch(&data_dir, self.headless).await {
            Ok(provider) => provider,
            Err(err) => {
                // Roll back the lease: a failed launch must not hold the profile.
                let _ = self.leases.revoke(&lease.id);
                return Err(err.into());
            },
        };

        let browser = BrowserHandle(Arc::new(Mutex::new(provider)));
        self.sessions.write().await.insert(
            lease.id.clone(),
            LiveSession {
                scope: scope.clone(),
                generation,
                holder,
                expires_at_unix_ms: lease.expires_at_unix_ms,
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
        self.sessions.write().await.remove(&lease_id);

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
        // live reader exists.
        if let Ok(provider) = Arc::try_unwrap(browser.0) {
            let _ = provider.into_inner().close().await;
        }
        let _ = self.leases.revoke(&lease.id);
        let _ = self
            .store
            .seal(&lease.principal, &lease.profile, generation);
        Ok(())
    }

    /// Every live session.
    pub async fn live(&self) -> Vec<LiveSessionInfo> {
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

    /// The browser for a specific lease.
    pub async fn browser(&self, lease_id: &str) -> Result<BrowserHandle> {
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
        let mut provider = browser.lock().await;
        Ok(provider.screenshot().await?)
    }
}
