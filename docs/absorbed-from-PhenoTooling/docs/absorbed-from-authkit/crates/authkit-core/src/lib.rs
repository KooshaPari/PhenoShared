//! Authentication and authorization framework.
//!
//! # Architecture
//!
//! AuthKit follows hexagonal architecture:
//!
//! - **Domain**: Pure business logic (identity, auth, policy)
//! - **Application**: Use cases and auth services
//! - **Adapters**: JWT, OAuth2, storage, hashers
//! - **Infrastructure**: Cross-cutting concerns (error handling, logging)
//!
//! # Quick Start
//!
//! ```
//! use authkit_core::{Authenticator, UserId, Role};
//!
//! let auth = Authenticator::new("secret_key");
//! let token = auth.generate_token(&UserId::new(), &[Role::new("admin")]);
//! ```

pub mod adapters;
pub mod application;
pub mod domain;
pub mod infrastructure;
pub mod middleware;

// Re-exports
pub use adapters::refresh_token::InMemoryRefreshTokenStore;
pub use adapters::revocation::InMemoryRevocationStore;
pub use application::services::AuthService;
pub use domain::auth::{Authenticator, RefreshClaims, TokenPair};
pub use domain::errors::AuthError;
pub use domain::pkce::{CodeChallenge, CodeVerifier, OAuthState};
pub use domain::policy::{Condition, Policy, PolicyEffect, PolicyEngine};
pub use domain::ports::{RefreshTokenStore, RevocationStore};
pub use domain::session_store::{InMemorySessionStore, SessionStore, SessionStoreError};
pub use domain::vault::{EncryptedBlob, SecretVault, VaultEntry, VaultError, VaultKey};
pub use domain::{Claims, Permission, Role, Session, SessionId, User, UserId};
pub use infrastructure::error::AuthKitError;
pub use middleware::{AuthKitMiddleware, AuthKitMiddlewareAdapter};

/// Framework version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
