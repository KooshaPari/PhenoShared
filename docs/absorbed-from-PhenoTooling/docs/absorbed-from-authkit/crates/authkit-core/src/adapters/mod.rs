//! Adapters layer.

pub mod audit;
pub mod hashers;
pub mod kms;
pub mod refresh_token;
pub mod revocation;
pub mod storage;
pub mod vault_store;

// Re-exports
pub use audit::{InMemoryAuditSink, TracingAuditSink};
pub use hashers::{Argon2Hasher, BcryptHasher};
pub use kms::LocalKmsAdapter;
pub use refresh_token::InMemoryRefreshTokenStore;
pub use revocation::InMemoryRevocationStore;
pub use storage::InMemoryUserStorage;
pub use vault_store::{FileVaultStore, InMemoryVaultStore};
