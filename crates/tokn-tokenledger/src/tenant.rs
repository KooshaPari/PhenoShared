//! Tenant isolation module — ADR-008 implementation.
//!
//! Provides types, validation, and resolution traits for multi-tenant
//! isolation in Tokn. Each tenant has an independent identity, tier,
//! and configuration namespace.
//!
//! Architecture (ADR-008):
//! ```text
//!   Client Request
//!     │ X-Tokn-Tenant-ID: tenant_abc
//!     ▼
//!   TenantResolver::resolve_tenant() → TenantContext
//!     │
//!     ├── TenantValidation::validate_tenant_id()
//!     ├── Key resolution → per-tenant signing keys
//!     └── Rate-limit & feature namespace
//! ```

use serde::{Deserialize, Serialize};
use std::fmt;

// =============================================================================
// Tenant Tier
// =============================================================================

/// Service tier for a tenant — governs rate limits, features, and quotas.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TenantTier {
    /// Free tier — limited rate limits, basic features.
    Free,
    /// Pro tier — higher limits, advanced features.
    Pro,
    /// Enterprise tier — custom limits, all features, dedicated support.
    Enterprise,
}

impl TenantTier {
    /// Returns true if this tier includes the features of `other`.
    pub fn encompasses(&self, other: &TenantTier) -> bool {
        match (self, other) {
            (TenantTier::Enterprise, _) => true,
            (TenantTier::Pro, TenantTier::Pro | TenantTier::Free) => true,
            (TenantTier::Pro, TenantTier::Enterprise) => false,
            (TenantTier::Free, TenantTier::Free) => true,
            (TenantTier::Free, _) => false,
        }
    }
}

impl fmt::Display for TenantTier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TenantTier::Free => write!(f, "free"),
            TenantTier::Pro => write!(f, "pro"),
            TenantTier::Enterprise => write!(f, "enterprise"),
        }
    }
}

// =============================================================================
// TenantError — typed auth/tenant failure errors
// =============================================================================

/// Typed error for tenant resolution and authorization failures.
///
/// Addresses audit finding L4: "Surface tenant/auth failures as
/// typed errors, not absent values."
#[derive(Debug, Clone, thiserror::Error)]
pub enum TenantError {
    /// The tenant ID does not match any known tenant.
    #[error("tenant not found: {0}")]
    TenantNotFound(String),

    /// The tenant exists but is inactive / disabled.
    #[error("tenant is inactive: {0}")]
    TenantInactive(String),

    /// The tenant ID string failed validation rules.
    #[error("invalid tenant ID: {0}")]
    InvalidTenantId(String),

    /// Detected tenant header spoofing — the provided identity does not
    /// match the cryptographic credential.
    #[error(
        "tenant spoofing detected: credential mismatch for tenant '{expected}', got claim '{actual}'"
    )]
    SpoofAttempt {
        /// The expected tenant extracted from the verified credential.
        expected: String,
        /// The tenant ID claimed in the untrusted header.
        actual: String,
    },

    /// The tenant is not authorized for the requested operation.
    #[error("tenant '{0}' not authorized for this operation")]
    Unauthorized(String),

    /// Internal resolution error (e.g., storage failure).
    #[error("tenant resolution error: {0}")]
    ResolutionError(String),
}

impl TenantError {
    /// Returns the tenant identifier associated with the error, if applicable.
    pub fn tenant_id(&self) -> Option<&str> {
        match self {
            TenantError::TenantNotFound(id)
            | TenantError::TenantInactive(id)
            | TenantError::InvalidTenantId(id)
            | TenantError::Unauthorized(id) => Some(id.as_str()),
            TenantError::SpoofAttempt { expected, .. } => Some(expected.as_str()),
            TenantError::ResolutionError(_) => None,
        }
    }
}

// =============================================================================
// TenantId — validated newtype
// =============================================================================

/// A validated tenant identifier.
///
/// Ensures the ID meets ADR-008 validation rules at construction time.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct TenantId(String);

impl TenantId {
    /// Maximum allowed length for a tenant ID (ADR-008).
    pub const MAX_LENGTH: usize = 64;

    /// Reserved IDs that cannot be used by external tenants.
    pub const RESERVED_IDS: &'static [&'static str] = &["system", "admin", "default"];

    /// Create a new `TenantId`, validating the input against ADR-008 rules.
    ///
    /// Returns `TenantError::InvalidTenantId` if validation fails.
    pub fn new(id: &str) -> Result<Self, TenantError> {
        Self::validate(id)?;
        Ok(Self(id.to_string()))
    }

    /// Create a `TenantId` without validation (for trusted/internal use).
    ///
    /// # Safety
    ///
    /// Caller must ensure the ID is pre-validated or from a trusted source.
    pub fn new_unchecked(id: &str) -> Self {
        Self(id.to_string())
    }

    /// Returns the underlying string.
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// ADR-008 validation rules.
    fn validate(id: &str) -> Result<(), TenantError> {
        if id.is_empty() {
            return Err(TenantError::InvalidTenantId(
                "tenant ID must not be empty".to_string(),
            ));
        }
        if id.len() > Self::MAX_LENGTH {
            return Err(TenantError::InvalidTenantId(format!(
                "tenant ID length {} exceeds maximum {}",
                id.len(),
                Self::MAX_LENGTH
            )));
        }
        if !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
        {
            return Err(TenantError::InvalidTenantId(
                "tenant ID must only contain alphanumeric characters, underscores, and hyphens"
                    .to_string(),
            ));
        }
        let lower = id.to_lowercase();
        if Self::RESERVED_IDS.contains(&lower.as_str()) {
            return Err(TenantError::InvalidTenantId(format!(
                "'{id}' is a reserved tenant ID"
            )));
        }
        Ok(())
    }
}

impl fmt::Display for TenantId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl AsRef<str> for TenantId {
    fn as_ref(&self) -> &str {
        &self.0
    }
}

// =============================================================================
// TenantContext — resolved tenant runtime information
// =============================================================================

/// Runtime context for an authenticated tenant (ADR-008 §Implementation).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TenantContext {
    /// The validated tenant identifier.
    pub tenant_id: TenantId,
    /// Service tier — governs rate limits and feature access.
    pub tier: TenantTier,
    /// Key identifier for per-tenant cryptographic key resolution.
    pub key_id: String,
    /// Feature flags enabled for this tenant.
    pub features: Vec<String>,
}

impl TenantContext {
    /// Check if a specific feature is enabled for this tenant.
    pub fn has_feature(&self, feature: &str) -> bool {
        self.features.iter().any(|f| f == feature)
    }
}

// =============================================================================
// TenantValidation — ADR-008 validation rules engine
// =============================================================================

/// Configuration and engine for tenant ID validation (ADR-008 §Validation Rules).
#[derive(Debug, Clone)]
pub struct TenantValidation {
    /// Maximum allowed length for tenant IDs.
    pub max_id_length: usize,
    /// Reserved IDs that cannot be used by external tenants.
    pub reserved_ids: Vec<String>,
}

impl Default for TenantValidation {
    fn default() -> Self {
        Self {
            max_id_length: TenantId::MAX_LENGTH,
            reserved_ids: TenantId::RESERVED_IDS
                .iter()
                .map(|s| s.to_string())
                .collect(),
        }
    }
}

impl TenantValidation {
    /// Validate a tenant ID string against all configured rules.
    ///
    /// Returns `Ok(())` if the ID is valid, or a descriptive `TenantError`.
    pub fn validate_tenant_id(&self, id: &str) -> Result<(), TenantError> {
        if id.is_empty() {
            return Err(TenantError::InvalidTenantId(
                "tenant ID must not be empty".to_string(),
            ));
        }
        if id.len() > self.max_id_length {
            return Err(TenantError::InvalidTenantId(format!(
                "tenant ID length {} exceeds maximum {}",
                id.len(),
                self.max_id_length
            )));
        }
        if !id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
        {
            return Err(TenantError::InvalidTenantId(
                "tenant ID must only contain alphanumeric characters, underscores, and hyphens"
                    .to_string(),
            ));
        }
        let lower = id.to_lowercase();
        if self.reserved_ids.contains(&lower) {
            return Err(TenantError::InvalidTenantId(format!(
                "'{id}' is a reserved tenant ID"
            )));
        }
        Ok(())
    }

    /// Anti-spoofing check: verifies that the tenant ID from an untrusted
    /// header matches the cryptographically verified tenant identity.
    ///
    /// This is the primary defense against tenant header spoofing
    /// (audit finding L18 / ADR-008 §Mitigation).
    pub fn verify_tenant_identity(
        &self,
        header_tenant_id: &str,
        credential_tenant_id: &str,
    ) -> Result<(), TenantError> {
        if header_tenant_id != credential_tenant_id {
            return Err(TenantError::SpoofAttempt {
                expected: credential_tenant_id.to_string(),
                actual: header_tenant_id.to_string(),
            });
        }
        Ok(())
    }
}

// =============================================================================
// TenantResolver trait — port for tenant resolution
// =============================================================================

/// Port (hexagonal architecture) for resolving a tenant ID to a `TenantContext`.
///
/// Implementations may resolve from a database, config file, or remote service.
#[async_trait::async_trait]
pub trait TenantResolver: Send + Sync {
    /// Resolve a tenant identifier to its full runtime context.
    ///
    /// Returns `TenantError::TenantNotFound` if the tenant does not exist,
    /// or `TenantError::TenantInactive` if the tenant is disabled.
    async fn resolve_tenant(&self, tenant_id: &TenantId) -> Result<TenantContext, TenantError>;

    /// Check whether a tenant is active (enabled and not suspended).
    async fn is_tenant_active(&self, tenant_id: &TenantId) -> Result<bool, TenantError>;
}

// =============================================================================
// InMemoryTenantResolver — simple test/development resolver
// =============================================================================

/// In-memory tenant resolver for testing and development.
///
/// Maintains a static map of known tenants.
pub struct InMemoryTenantResolver {
    tenants: std::collections::HashMap<String, TenantContext>,
}

impl InMemoryTenantResolver {
    /// Create a new empty resolver.
    pub fn new() -> Self {
        Self {
            tenants: std::collections::HashMap::new(),
        }
    }

    /// Register a tenant context.
    pub fn register(&mut self, ctx: TenantContext) {
        self.tenants.insert(ctx.tenant_id.as_str().to_string(), ctx);
    }
}

impl Default for InMemoryTenantResolver {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait::async_trait]
impl TenantResolver for InMemoryTenantResolver {
    async fn resolve_tenant(&self, tenant_id: &TenantId) -> Result<TenantContext, TenantError> {
        self.tenants
            .get(tenant_id.as_str())
            .cloned()
            .ok_or_else(|| TenantError::TenantNotFound(tenant_id.to_string()))
    }

    async fn is_tenant_active(&self, tenant_id: &TenantId) -> Result<bool, TenantError> {
        Ok(self.tenants.contains_key(tenant_id.as_str()))
    }
}

// =============================================================================
// Rate limit configuration stub (ADR-008 references)
// =============================================================================

/// Per-tenant rate limit configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    /// Maximum requests per minute.
    pub requests_per_minute: u32,
    /// Maximum tokens per minute.
    pub tokens_per_minute: u64,
    /// Burst allowance multiplier.
    pub burst_multiplier: f64,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            requests_per_minute: 60,
            tokens_per_minute: 100_000,
            burst_multiplier: 2.0,
        }
    }
}

// =============================================================================
// Feature flags
// =============================================================================

/// Well-known feature flag constants.
pub mod features {
    /// Access to audit log export.
    pub const AUDIT_LOG: &str = "audit_log";
    /// Access to custom rate limit configuration.
    pub const CUSTOM_RATE_LIMITS: &str = "custom_rate_limits";
    /// Access to advanced routing strategies.
    pub const ADVANCED_ROUTING: &str = "advanced_routing";
    /// Access to batch processing.
    pub const BATCH_PROCESSING: &str = "batch_processing";
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    // ── TenantId validation ─────────────────────────────────────────────

    #[test]
    fn test_tenant_id_valid() {
        let id = TenantId::new("tenant_abc-123").expect("valid tenant ID");
        assert_eq!(id.as_str(), "tenant_abc-123");
    }

    #[test]
    fn test_tenant_id_empty() {
        let err = TenantId::new("").unwrap_err();
        assert!(matches!(err, TenantError::InvalidTenantId(_)));
        assert!(err.to_string().contains("empty"));
    }

    #[test]
    fn test_tenant_id_too_long() {
        let long = "a".repeat(65);
        let err = TenantId::new(&long).unwrap_err();
        assert!(matches!(err, TenantError::InvalidTenantId(_)));
        assert!(err.to_string().contains("exceeds maximum"));
    }

    #[test]
    fn test_tenant_id_invalid_chars() {
        let err = TenantId::new("tenant with spaces").unwrap_err();
        assert!(matches!(err, TenantError::InvalidTenantId(_)));

        let err = TenantId::new("tenant@special!").unwrap_err();
        assert!(matches!(err, TenantError::InvalidTenantId(_)));
    }

    #[test]
    fn test_tenant_id_reserved() {
        // Reserved IDs should be rejected (case-insensitive)
        for &reserved in TenantId::RESERVED_IDS {
            let err = TenantId::new(reserved).unwrap_err();
            assert!(
                matches!(err, TenantError::InvalidTenantId(_)),
                "expected error for reserved ID '{reserved}'"
            );
        }

        // Also test uppercase version of reserved
        let err = TenantId::new("Admin").unwrap_err();
        assert!(matches!(err, TenantError::InvalidTenantId(_)));
    }

    #[test]
    fn test_tenant_id_max_length_boundary() {
        // 64 chars should be valid
        let ok = "a".repeat(TenantId::MAX_LENGTH);
        assert!(TenantId::new(&ok).is_ok());

        // 65 chars should fail
        let too_long = "a".repeat(TenantId::MAX_LENGTH + 1);
        assert!(TenantId::new(&too_long).is_err());
    }

    #[test]
    fn test_tenant_id_display() {
        let id = TenantId::new("my-tenant").unwrap();
        assert_eq!(format!("{id}"), "my-tenant");
        assert_eq!(id.to_string(), "my-tenant");
    }

    #[test]
    fn test_tenant_id_as_ref() {
        let id = TenantId::new("my-tenant").unwrap();
        let s: &str = id.as_ref();
        assert_eq!(s, "my-tenant");
    }

    // ── TenantError ─────────────────────────────────────────────────────

    #[test]
    fn test_tenant_error_tenant_id_extraction() {
        let err = TenantError::TenantNotFound("tenant-1".to_string());
        assert_eq!(err.tenant_id(), Some("tenant-1"));

        let err = TenantError::SpoofAttempt {
            expected: "real-tenant".to_string(),
            actual: "fake-tenant".to_string(),
        };
        assert_eq!(err.tenant_id(), Some("real-tenant"));

        let err = TenantError::ResolutionError("db down".to_string());
        assert_eq!(err.tenant_id(), None);
    }

    #[test]
    fn test_tenant_error_display() {
        let err = TenantError::TenantNotFound("xyz".to_string());
        assert_eq!(err.to_string(), "tenant not found: xyz");

        let err = TenantError::SpoofAttempt {
            expected: "real".to_string(),
            actual: "fake".to_string(),
        };
        assert!(err.to_string().contains("spoofing"));
    }

    // ── TenantValidation ────────────────────────────────────────────────

    #[test]
    fn test_validation_default_config() {
        let v = TenantValidation::default();
        assert_eq!(v.max_id_length, 64);
        assert!(v.reserved_ids.contains(&"system".to_string()));
    }

    #[test]
    fn test_validation_accepts_valid_ids() {
        let v = TenantValidation::default();
        assert!(v.validate_tenant_id("my-tenant-123").is_ok());
        assert!(v.validate_tenant_id("test_abc").is_ok());
        assert!(v.validate_tenant_id("a1b2c3").is_ok());
    }

    #[test]
    fn test_validation_rejects_bad_ids() {
        let v = TenantValidation::default();
        assert!(v.validate_tenant_id("").is_err());
        assert!(v.validate_tenant_id("has space").is_err());
        assert!(v.validate_tenant_id("special!chars").is_err());
        assert!(v.validate_tenant_id("admin").is_err());
        assert!(v.validate_tenant_id("SYSTEM").is_err());
    }

    // ── Anti-spoofing check ─────────────────────────────────────────────

    #[test]
    fn test_verify_tenant_identity_match() {
        let v = TenantValidation::default();
        assert!(v.verify_tenant_identity("tenant-1", "tenant-1").is_ok());
    }

    #[test]
    fn test_verify_tenant_identity_mismatch() {
        let v = TenantValidation::default();
        let err = v
            .verify_tenant_identity("header-tenant", "credential-tenant")
            .unwrap_err();
        assert!(matches!(err, TenantError::SpoofAttempt { .. }));
        if let TenantError::SpoofAttempt { expected, actual } = &err {
            assert_eq!(expected, "credential-tenant");
            assert_eq!(actual, "header-tenant");
        }
    }

    // ── TenantTier ──────────────────────────────────────────────────────

    #[test]
    fn test_tenant_tier_encompasses() {
        assert!(TenantTier::Enterprise.encompasses(&TenantTier::Free));
        assert!(TenantTier::Enterprise.encompasses(&TenantTier::Pro));
        assert!(TenantTier::Enterprise.encompasses(&TenantTier::Enterprise));
        assert!(TenantTier::Pro.encompasses(&TenantTier::Free));
        assert!(TenantTier::Pro.encompasses(&TenantTier::Pro));
        assert!(!TenantTier::Pro.encompasses(&TenantTier::Enterprise));
        assert!(TenantTier::Free.encompasses(&TenantTier::Free));
        assert!(!TenantTier::Free.encompasses(&TenantTier::Pro));
        assert!(!TenantTier::Free.encompasses(&TenantTier::Enterprise));
    }

    #[test]
    fn test_tenant_tier_display() {
        assert_eq!(TenantTier::Free.to_string(), "free");
        assert_eq!(TenantTier::Pro.to_string(), "pro");
        assert_eq!(TenantTier::Enterprise.to_string(), "enterprise");
    }

    // ── TenantContext ───────────────────────────────────────────────────

    #[test]
    fn test_tenant_context_has_feature() {
        let ctx = TenantContext {
            tenant_id: TenantId::new_unchecked("test-tenant"),
            tier: TenantTier::Pro,
            key_id: "key-1".to_string(),
            features: vec!["audit_log".to_string(), "batch_processing".to_string()],
        };
        assert!(ctx.has_feature("audit_log"));
        assert!(ctx.has_feature("batch_processing"));
        assert!(!ctx.has_feature("advanced_routing"));
    }

    #[test]
    fn test_tenant_context_serialization() {
        let ctx = TenantContext {
            tenant_id: TenantId::new_unchecked("tenant-1"),
            tier: TenantTier::Enterprise,
            key_id: "ek-abc123".to_string(),
            features: vec!["audit_log".to_string()],
        };
        let json = serde_json::to_string(&ctx).expect("serialize");
        let deserialized: TenantContext = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(deserialized.tenant_id.as_str(), "tenant-1");
        assert_eq!(deserialized.tier, TenantTier::Enterprise);
        assert_eq!(deserialized.key_id, "ek-abc123");
    }

    // ── InMemoryTenantResolver ──────────────────────────────────────────

    #[tokio::test]
    async fn test_in_memory_resolver_resolve_known_tenant() {
        let mut resolver = InMemoryTenantResolver::new();
        let ctx = TenantContext {
            tenant_id: TenantId::new_unchecked("tenant-alpha"),
            tier: TenantTier::Pro,
            key_id: "key-alpha".to_string(),
            features: vec![],
        };
        resolver.register(ctx);

        let id = TenantId::new_unchecked("tenant-alpha");
        let resolved = resolver.resolve_tenant(&id).await.expect("should resolve");
        assert_eq!(resolved.tenant_id.as_str(), "tenant-alpha");
        assert_eq!(resolved.tier, TenantTier::Pro);
    }

    #[tokio::test]
    async fn test_in_memory_resolver_resolve_unknown_tenant() {
        let resolver = InMemoryTenantResolver::new();
        let id = TenantId::new_unchecked("unknown-tenant");
        let err = resolver.resolve_tenant(&id).await.unwrap_err();
        assert!(matches!(err, TenantError::TenantNotFound(_)));
    }

    #[tokio::test]
    async fn test_in_memory_resolver_is_active() {
        let mut resolver = InMemoryTenantResolver::new();
        let ctx = TenantContext {
            tenant_id: TenantId::new_unchecked("active-tenant"),
            tier: TenantTier::Free,
            key_id: "key".to_string(),
            features: vec![],
        };
        resolver.register(ctx);

        let active_id = TenantId::new_unchecked("active-tenant");
        assert!(
            resolver
                .is_tenant_active(&active_id)
                .await
                .expect("check active")
        );

        let unknown_id = TenantId::new_unchecked("unknown");
        assert!(
            !resolver
                .is_tenant_active(&unknown_id)
                .await
                .expect("check unknown")
        );
    }

    // ── RateLimitConfig ─────────────────────────────────────────────────

    #[test]
    fn test_rate_limit_config_default() {
        let cfg = RateLimitConfig::default();
        assert_eq!(cfg.requests_per_minute, 60);
        assert_eq!(cfg.tokens_per_minute, 100_000);
        assert!((cfg.burst_multiplier - 2.0).abs() < f64::EPSILON);
    }
}
