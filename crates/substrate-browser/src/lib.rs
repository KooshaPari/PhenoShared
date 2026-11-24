//! `substrate-browser` - profile generation store and lease authority for
//! browser automation.
//!
//! # Why
//!
//! Agent-driven browser work on this device is real but single-profile: one
//! browser profile is shared by every concurrent worker, so two agents driving
//! two windows of the same origin share cookies, storage and authenticated
//! session state. A window is a view, not an isolation boundary.
//!
//! Two primitives are missing before concurrent agents can be trusted:
//!
//! 1. **Profile generation isolation** ([`ProfileStore`]) - each principal owns
//!    named profiles, each profile is a numbered *generation* backed by its own
//!    browser data directory, and a generation is only ever promoted by
//!    compare-and-swap. A stopped generation can be forked for a new identity
//!    without ever merging two browser databases.
//! 2. **Lease authority** ([`LeaseManager`]) - a single writer per profile,
//!    granted with a TTL and a monotonic fencing token, so a stale or expired
//!    holder can be detected and cannot act.
//!
//! Neither primitive launches or drives a browser. They are the state layer a
//! broker sits on, deliberately kept free of browser-specific code so the same
//! authority covers Firefox, Chrome/CDP and remote workers.
//!
//! # Safety default
//!
//! Mutating operations on [`ProfileStore`] consult a [`LeaseGate`] when one is
//! configured. A store built with [`ProfileStore::with_gate`] therefore cannot
//! promote or delete a generation out from under a live lease. A store built by
//! [`ProfileStore::new`] is unguarded and is intended for single-process setup
//! and tests only; production callers must wire a gate.
//!
//! # Layout
//!
//! ```text
//! <root>/
//!   profiles/<principal>/<profile>/manifest.json
//!   profiles/<principal>/<profile>/gen-<n>/          # browser user-data-dir
//!   leases/<lease-id>.json
//!   fences.json                                      # monotonic fence per profile
//!   leases.lock                                      # cross-process advisory lock
//! ```

#![deny(missing_docs)]

mod fsutil;
mod lease;
mod procutil;
mod profile;
mod scope;

pub use lease::{Clock, Lease, LeaseGate, LeaseManager, SystemClock};
pub use profile::{Generation, ProfileStore};
pub use scope::{Scope, ScopeError};

use thiserror::Error;

/// Errors produced by the browser state layer.
#[derive(Debug, Error)]
pub enum BrowserError {
    /// A caller-supplied scope was malformed or unsafe.
    #[error("invalid scope: {0}")]
    Scope(#[from] ScopeError),

    /// The requested profile or generation does not exist.
    #[error("no such generation {generation} in profile {principal}/{profile}")]
    UnknownGeneration {
        /// Principal that owns the profile.
        principal: String,
        /// Profile name.
        profile: String,
        /// Requested generation number.
        generation: u64,
    },

    /// A compare-and-swap on the active generation did not match.
    #[error("generation promotion conflict: expected active {expected}, found {actual:?}")]
    PromotionConflict {
        /// Generation the caller believed was active.
        expected: u64,
        /// Generation actually recorded as active.
        actual: Option<u64>,
    },

    /// The operation would have discarded or mutated a live holder's state.
    #[error("refused: {0}")]
    Refused(String),

    /// A lease was not found.
    #[error("no such lease {0}")]
    UnknownLease(String),

    /// A lease exists but must not be used.
    #[error("lease {id} is not usable: {reason}")]
    LeaseUnusable {
        /// Lease identifier.
        id: String,
        /// Human-readable reason.
        reason: String,
    },

    /// A fencing token did not match the current holder.
    #[error("stale fencing token {presented} for lease {id} (current {current})")]
    StaleFence {
        /// Lease identifier.
        id: String,
        /// Token presented by the caller.
        presented: u64,
        /// Token currently issued for the profile.
        current: u64,
    },

    /// Filesystem or serialization failure.
    #[error("browser state store error: {0}")]
    Io(#[from] std::io::Error),
}

/// Result alias for this crate.
pub type Result<T> = std::result::Result<T, BrowserError>;
