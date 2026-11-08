//! Lease-fenced action surface for one live browser.
//!
//! A [`BrowserHandle`] is `Clone`, so it can outlive the lease that created it.
//! Authority is therefore re-proved against the on-disk lease record before
//! every action, and the provider guard never escapes this module. A caller gets
//! a named action, not a long-lived mutable reference, so there is no way to
//! hold authority past the check that granted it.

use std::{
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    time::Duration,
};

use substrate_browser_cdp::{CdpProvider, FenceCheck};
use tokio::sync::{Mutex, MutexGuard};

use crate::{lease_guard::LeaseGuard, BrokerError, Result};

/// How long one action may wait for the browser before the broker refuses.
const HOLD_TIMEOUT: Duration = Duration::from_secs(30);

/// A handle to one live browser, shared between the caller and the viewer.
#[derive(Clone)]
pub struct BrowserHandle {
    provider: Arc<Mutex<Option<CdpProvider>>>,
    guard: LeaseGuard,
    revoked: Arc<AtomicBool>,
}

impl BrowserHandle {
    /// Bind a freshly launched browser to the lease that authorised it.
    pub(crate) fn new(mut provider: CdpProvider, guard: LeaseGuard) -> Self {
        // Per-message enforcement: the transport re-proves the lease before
        // every CDP command, so an action that spans several commands cannot
        // outlive the lease between them.
        let fence: std::sync::Arc<dyn FenceCheck> = std::sync::Arc::new(guard.clone());
        provider.set_fence(Some(fence));
        Self {
            provider: Arc::new(Mutex::new(Some(provider))),
            guard,
            revoked: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Lease identifier this handle is bound to.
    pub fn lease_id(&self) -> &str {
        self.guard.lease_id()
    }

    /// Re-prove the lease, then take the browser for one action.
    ///
    /// The provider guard is private on purpose. A caller is handed a named
    /// action, never a long-lived `&mut CdpProvider`, so authority cannot
    /// outlive the lease check that authorised it. The wait for the browser is
    /// bounded: a stuck DevTools call fails the action instead of wedging the
    /// broker.
    async fn acquire(&self) -> Result<MutexGuard<'_, Option<CdpProvider>>> {
        self.guard.check()?;
        if self.revoked.load(Ordering::SeqCst) {
            return Err(self.released());
        }
        let held = match tokio::time::timeout(HOLD_TIMEOUT, self.provider.lock()).await {
            Ok(held) => held,
            Err(_) => return Err(self.busy()),
        };
        // Waiting may have outlived the lease, so prove it again.
        self.guard.check()?;
        if self.revoked.load(Ordering::SeqCst) {
            return Err(self.released());
        }
        Ok(held)
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
