//! Lease-fenced action surface for one live browser.
//!
//! A [`BrowserHandle`] is `Clone`, so it can outlive the lease that created it.
//! Authority is therefore re-proved against the on-disk lease record before
//! every action, and the provider guard never escapes this module. A caller gets
//! a named action, not a long-lived mutable reference, so there is no way to
//! hold authority past the check that granted it.
//!
//! # Deferred launch
//!
//! The browser is launched on the **first action**, not when the lease is
//! granted. Launching a Chrome takes tens of seconds on a loaded host, so doing
//! it inside `acquire` made every lease grant as expensive as a browser start
//! and pushed the HTTP acquire call past any sane client timeout. A handle now
//! carries the launch parameters and fills its provider slot on demand.

use std::{
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    time::Duration,
};

use substrate_browser_cdp::{CdpProvider, FenceCheck};
use tokio::sync::{Mutex, MutexGuard};

use crate::{lease_guard::LeaseGuard, BrokerError, Result};

/// How long one action may wait for the browser lock before the broker refuses.
///
/// Covers a deferred launch plus one real action (a screenshot of a live page
/// takes seconds), so a concurrent caller waits instead of failing while the
/// first caller is legitimately holding the browser.
const HOLD_TIMEOUT: Duration = Duration::from_secs(120);

/// How long a deferred launch may take before the action fails.
///
/// Chrome's own CDP connect is bounded at 30s; this outer bound covers a cold
/// start on a loaded host without letting a wedged launch hold the lease lock
/// forever.
const LAUNCH_TIMEOUT: Duration = Duration::from_secs(120);

/// Everything needed to start this handle's browser on first use.
#[derive(Clone, Debug)]
pub(crate) struct LaunchSpec {
    /// The generation's user data directory.
    pub data_dir: PathBuf,
    /// Run with a window (`false`) or headless (`true`).
    pub headless: bool,
}

/// A handle to one live browser, shared between the caller and the viewer.
#[derive(Clone)]
pub struct BrowserHandle {
    provider: Arc<Mutex<Option<CdpProvider>>>,
    launch: Arc<LaunchSpec>,
    guard: LeaseGuard,
    revoked: Arc<AtomicBool>,
    /// Set after a deferred launch failed, so a broken launch is not retried on
    /// every subsequent action (the lease is revoked at that point anyway).
    launch_failed: Arc<AtomicBool>,
}

impl BrowserHandle {
    /// Bind a not-yet-launched browser to the lease that authorises it.
    ///
    /// No process is started here: the first action launches the browser.
    pub(crate) fn new(launch: LaunchSpec, guard: LeaseGuard) -> Self {
        Self {
            provider: Arc::new(Mutex::new(None)),
            launch: Arc::new(launch),
            guard,
            revoked: Arc::new(AtomicBool::new(false)),
            launch_failed: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Lease identifier this handle is bound to.
    pub fn lease_id(&self) -> &str {
        self.guard.lease_id()
    }

    /// Whether this handle has launched its browser yet.
    ///
    /// Observability only; it never triggers a launch.
    pub async fn is_launched(&self) -> bool {
        self.provider.lock().await.is_some()
    }

    /// Re-prove the lease, then take the browser for one action.
    ///
    /// The provider guard is private on purpose. A caller is handed a named
    /// action, never a long-lived `&mut CdpProvider`, so authority cannot
    /// outlive the lease check that authorised it. The wait for the browser is
    /// bounded: a stuck DevTools call fails the action instead of wedging the
    /// broker.
    ///
    /// When the slot is still empty this launches the browser, and re-proves the
    /// lease afterwards: a lease that died during the launch must not be handed
    /// a browser.
    async fn acquire(&self) -> Result<MutexGuard<'_, Option<CdpProvider>>> {
        self.guard.check()?;
        if self.revoked.load(Ordering::SeqCst) {
            return Err(self.released());
        }
        let mut held = match tokio::time::timeout(HOLD_TIMEOUT, self.provider.lock()).await {
            Ok(held) => held,
            Err(_) => return Err(self.busy()),
        };
        // Waiting may have outlived the lease, so prove it again.
        self.guard.check()?;
        if self.revoked.load(Ordering::SeqCst) {
            return Err(self.released());
        }
        if held.is_none() {
            self.launch_locked(&mut held).await?;
        }
        Ok(held)
    }

    /// Fill the provider slot, or fail having revoked the lease.
    ///
    /// Two invariants hang off this moment:
    ///
    /// * a failed launch must not hold the profile - the lease record is
    ///   revoked and the handle is marked revoked, so nothing keeps the profile
    ///   busy for the rest of the TTL;
    /// * a browser is never handed out under a dead lease - the guard is proved
    ///   again after the launch (which can take longer than the remaining TTL),
    ///   and a browser that lost its lease is closed immediately.
    async fn launch_locked(&self, held: &mut Option<CdpProvider>) -> Result<()> {
        if self.launch_failed.load(Ordering::SeqCst) {
            return Err(self.released());
        }
        let launched = match tokio::time::timeout(
            LAUNCH_TIMEOUT,
            CdpProvider::launch(&self.launch.data_dir, self.launch.headless),
        )
        .await
        {
            Ok(Ok(provider)) => provider,
            Ok(Err(err)) => {
                self.abandon();
                return Err(err.into());
            },
            Err(_) => {
                self.abandon();
                return Err(self.busy());
            },
        };

        // The launch may have outlived the lease. Close the browser and refuse.
        if let Err(err) = self.guard.check() {
            let _ = launched.close().await;
            self.abandon();
            return Err(err);
        }
        if self.revoked.load(Ordering::SeqCst) {
            let _ = launched.close().await;
            self.abandon();
            return Err(self.released());
        }

        // Per-message enforcement: the transport re-proves the lease before
        // every CDP command, so an action that spans several commands cannot
        // outlive the lease between them.
        let mut launched = launched;
        let fence: Arc<dyn FenceCheck> = Arc::new(self.guard.clone());
        launched.set_fence(Some(fence));
        *held = Some(launched);
        Ok(())
    }

    /// Give up this handle: revoke the lease so the profile is not held by a
    /// browser that never came up.
    fn abandon(&self) {
        self.launch_failed.store(true, Ordering::SeqCst);
        self.revoked.store(true, Ordering::SeqCst);
        let _ = self.guard.revoke();
    }

    async fn provider(&self) -> Result<MutexGuard<'_, Option<CdpProvider>>> {
        self.acquire().await
    }

    /// Navigate the page.
    pub async fn open(&self, url: &str) -> Result<()> {
        let mut held = self.provider().await?;
        held.as_mut()
            .ok_or_else(|| self.released())?
            .open(url)
            .await?;
        Ok(())
    }

    /// Capture a normalized page snapshot.
    pub async fn snapshot(&self) -> Result<substrate_browser_cdp::Snapshot> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        Ok(provider.snapshot().await?)
    }

    /// Click an element reference from the last snapshot.
    pub async fn click(&self, element_ref: &str) -> Result<()> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        provider.click(element_ref).await?;
        Ok(())
    }

    /// Type into an element reference, optionally submitting its form.
    pub async fn type_into(&self, element_ref: &str, text: &str, submit: bool) -> Result<()> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        provider.type_into(element_ref, text, submit).await?;
        Ok(())
    }

    /// Wait for text to appear.
    pub async fn wait_for_text(&self, needle: &str, timeout: Duration) -> Result<bool> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        Ok(provider.wait_for_text(needle, timeout).await?)
    }

    /// Capture a PNG of the page.
    pub async fn screenshot(&self) -> Result<Vec<u8>> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        Ok(provider.screenshot().await?)
    }

    /// Evaluate a JavaScript expression.
    pub async fn eval(&self, expression: &str) -> Result<serde_json::Value> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        Ok(provider.eval(expression).await?)
    }

    /// Page title.
    pub async fn title(&self) -> Result<String> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        Ok(provider.title().await?)
    }

    /// Page URL.
    pub async fn url(&self) -> Result<String> {
        let mut held = self.provider().await?;
        let provider = held.as_mut().ok_or_else(|| self.released())?;
        Ok(provider.url().await?)
    }

    /// Operating system process id of the backing browser.
    pub async fn pid(&self) -> Result<Option<u32>> {
        let held = self.provider().await?;
        Ok(held.as_ref().ok_or_else(|| self.released())?.pid())
    }

    fn released(&self) -> BrokerError {
        BrokerError::Released {
            lease: self.guard.lease_id().to_string(),
        }
    }

    fn busy(&self) -> BrokerError {
        BrokerError::Busy {
            lease: self.guard.lease_id().to_string(),
        }
    }

    /// Stop the browser bound to this handle, before its lease is revoked.
    ///
    /// Revokes every clone in-process first, then waits a bounded time for
    /// exclusive access so an in-flight action can finish, then kills and reaps
    /// the process. Only this function empties the provider slot.
    ///
    /// A handle whose browser was never launched has nothing to close, so this
    /// succeeds without starting one.
    pub(crate) async fn shutdown(&self) -> Result<()> {
        self.revoked.store(true, Ordering::SeqCst);
        let provider = match tokio::time::timeout(HOLD_TIMEOUT, self.provider.lock()).await {
            Ok(mut slot) => slot.take(),
            // A stuck action still holds the provider. Report it rather than
            // claiming the browser stopped.
            Err(_) => return Err(self.busy()),
        };
        match provider {
            // Already stopped by an earlier release or purge.
            None => Ok(()),
            // `close` consumes the provider, and `CdpProvider` kills its child
            // on drop, so even a timed-out close leaves no live browser behind.
            Some(provider) => match tokio::time::timeout(HOLD_TIMEOUT, provider.close()).await {
                Ok(outcome) => Ok(outcome?),
                Err(_) => Err(self.busy()),
            },
        }
    }
}

impl std::fmt::Debug for BrowserHandle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("BrowserHandle").finish_non_exhaustive()
    }
}
