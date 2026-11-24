//! Fail-closed lease enforcement for handles that outlive their lease.
//!
//! A [`crate::BrowserHandle`] is `Clone`, so a caller can keep using it after
//! release, after the TTL elapsed, or after another process superseded the
//! profile with a later grant. Cloning a handle must never extend authority,
//! therefore every action re-proves the lease against the on-disk
//! [`LeaseManager`], which is the cross-process authority (advisory file lock
//! plus monotonic per-profile fencing tokens).
//!
//! The guard checks, in order, that the lease record still exists, that it has
//! not expired on the manager's clock, and that the presented fencing token is
//! still the current one. Any failure is an error; there is no degraded mode.

use std::sync::Arc;

use substrate_browser::{Lease, LeaseManager};
use substrate_browser_cdp::FenceCheck;

use crate::Result;

/// A lease identity that must be re-validated before each action.
#[derive(Clone)]
pub struct LeaseGuard {
    leases: Arc<LeaseManager>,
    lease_id: String,
    fencing_token: u64,
}

impl LeaseGuard {
    /// Build a guard for `lease`, validated against `leases`.
    pub fn new(leases: Arc<LeaseManager>, lease: &Lease) -> Self {
        Self {
            leases,
            lease_id: lease.id.clone(),
            fencing_token: lease.fencing_token,
        }
    }

    /// Lease identifier this guard authorises.
    pub fn lease_id(&self) -> &str {
        &self.lease_id
    }

    /// Re-validate the lease, returning its current record on success.
    ///
    /// Fails if the lease was revoked (record gone), expired, or superseded by
    /// a later grant on the same profile.
    pub fn check(&self) -> Result<Lease> {
        Ok(self.leases.validate(&self.lease_id, self.fencing_token)?)
    }

    /// Withdraw the lease this guard authorises.
    ///
    /// Used when a deferred browser launch fails: a failed launch must not hold
    /// the profile, so the record is revoked immediately rather than left to
    /// expire. A record that is already gone counts as revoked, so this is safe
    /// to call on a lease that was reaped or superseded in the meantime.
    pub(crate) fn revoke(&self) -> Result<()> {
        match self.leases.revoke(&self.lease_id) {
            Ok(()) => Ok(()),
            Err(substrate_browser::BrowserError::UnknownLease(_)) => Ok(()),
            Err(err) => Err(err.into()),
        }
    }
}

impl std::fmt::Debug for LeaseGuard {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("LeaseGuard")
            .field("lease_id", &self.lease_id)
            .field("fencing_token", &self.fencing_token)
            .finish_non_exhaustive()
    }
}

impl FenceCheck for LeaseGuard {
    fn check(&self) -> std::result::Result<(), String> {
        // Explicit path: the inherent `check` wins resolution, so name it.
        LeaseGuard::check(self)
            .map(|_| ())
            .map_err(|err| err.to_string())
    }
}
