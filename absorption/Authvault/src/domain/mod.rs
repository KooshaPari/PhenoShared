//! Domain layer - pure authentication and authorization logic.

pub mod auth;
pub mod errors;
pub mod identity;
pub mod pkce;
pub mod policy;
pub mod ports;
pub mod session;
pub mod session_store;
pub mod signing;
pub mod vault;

// Re-exports
pub use auth::{AuthMethod, Authenticator, Claims};
pub use errors::AuthError;
pub use identity::{Permission, Role, User, UserId};
pub use pkce::{CodeChallenge, CodeVerifier, OAuthState};
pub use policy::{Condition, Policy, PolicyEffect, PolicyEngine};
pub use ports::{
    AuditAction, AuditEvent, AuditOutcome, AuditSink, PasswordHasher, RefreshTokenStore,
    RevocationStore, SessionStorage, UserStorage,
};
pub use session::{Session, SessionId};
pub use session_store::{InMemorySessionStore, SessionStore, SessionStoreError};
pub use signing::SigningKey;
pub use vault::{EncryptedBlob, SecretVault, VaultEntry, VaultError, VaultKey};
