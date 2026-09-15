//! Bifrost-backed router adapter for `OmniRoute` v1.5.
//!
//! This crate is the v1.5 pivot target per `D-omni-02` (sign-off at
//! `docs/sessions/20260705-omniroute-backend-rewrite/05-decisions/00-D-OMNI-SIGNOFF.md`).
//! v1 ships with `omni-router` as the placeholder; v1.5 swaps that out for a
//! Bifrost-backed implementation behind the same `RouterPort` trait
//! (defined in `omni-core::executor`).
//!
//! The crate exposes:
//!
//! 1. [`RouterPort`] — the trait contract that any v1/v1.5 router must
//!    satisfy. Today: `InMemoryRouter`, a deterministic router used by tests
//!    and by the v1 placeholder wiring.
//! 2. [`BifrostBackend`] — the v1.5 client stub. It currently fails every
//!    request with [`Error::BackendUnavailable`] so the v1.5 path can be
//!    wired into the dispatch loop without falsely succeeding.
//! 3. [`FallbackRouter`] — the B1 adapter. Composes a primary router with a
//!    fallback router; falls back only on `Error::BackendUnavailable`. Any
//!    other error propagates unchanged (R-omni-1 mitigation: no silent
//!    swallowing).
//!
//! See: `docs/ROUTING-CONVERGENCE-STATUS.md` § "Tier-1 / Tier-2 Router Split"
//! and the v8.1 Bifrost rollout plan (`PLAN.md` § 2.5.2, items B1-B9).

#![forbid(unsafe_code)]
#![warn(clippy::all, clippy::pedantic)]
#![allow(clippy::module_name_repetitions)]

pub mod backend;
#[cfg(feature = "cache-sqlite")]
pub mod cache;
pub mod catalog;
pub mod error;
pub mod fallback;
pub mod router;
pub mod sweeper;
#[cfg(feature = "virtual-keys")]
pub mod virtual_key;

pub use backend::BifrostBackend;
#[cfg(feature = "cache-sqlite")]
pub use cache::{BifrostModelCache, ProviderMeta, DEFAULT_TTL_SECS, MAX_ENTRIES_PER_PROVIDER};
#[cfg(feature = "catalog-fetch")]
pub use catalog::live::CatalogFetcher;
#[allow(unused_imports)]
pub use catalog::{
    CatalogEntry, CatalogWire, InMemoryCatalog, LookupOutcome, ModelCatalog, MAX_CATALOG_ENTRIES,
};
pub use error::{Error, Result};
pub use fallback::FallbackRouter;
pub use router::{InMemoryRouter, RouteTarget, RouterPort};
#[cfg(feature = "virtual-keys")]
pub use virtual_key::{TokenStatus, VirtualKey, VirtualKeyStore};
