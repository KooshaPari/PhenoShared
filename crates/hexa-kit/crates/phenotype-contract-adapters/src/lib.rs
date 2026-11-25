//! HexaKit scaffold adapters for hexagonal ports.
//!
//! In-memory implementations used by `phenotype-core` re-exports. Canonical
//! contract traits: slice crates on Authvault/Eventra/Agentora; generic `Contract` interim phenoShared.

pub mod adapters;
pub mod error;
pub mod outbound;

pub use adapters::{InMemoryCache, InMemoryEventBus, InMemoryRepository, InMemorySecretManager};
