//! Integration tests for tenant isolation (ADR-008 / audit L11-L12).
//!
//! These tests validate:
//! - Tenant ID validation rules against the ADR-008 spec
//! - Anti-spoofing verification (L18 mitigation)
//! - TenantContext resolution via InMemoryTenantResolver
//! - Cross-tenant isolation guarantees
//! - Typed error propagation through PortError (L4 correction)

use tokenledger::tenant::{
    InMemoryTenantResolver, RateLimitConfig, TenantContext, TenantError, TenantId, TenantResolver,
    TenantTier, TenantValidation, features,
};

// =============================================================================
// L11-L12: Tenant ID validation integration
// =============================================================================

#[test]
fn integration_tenant_id_validation_happy_path() {
    // Various valid tenant IDs that should pass ADR-008 validation
    let valid_ids = [
        "acme-corp",
        "startup_42",
        "tenant-abc-123",
        "a",
        "A",
        "Z_-9",
    ];
    for id in &valid_ids {
        TenantId::new(id).unwrap_or_else(|e| panic!("expected valid ID '{id}': {e}"));
    }
}

#[test]
fn integration_tenant_id_validation_edge_cases() {
    let v = TenantValidation::default();

    // Boundary: maximum length should be exactly 64
    let max_len = "a".repeat(64);
    assert!(
        v.validate_tenant_id(&max_len).is_ok(),
        "64 chars should be valid"
    );

    // Boundary: 65 chars should fail
    let too_long = "b".repeat(65);
    assert!(v.validate_tenant_id(&too_long).is_err());

    // Very long but < max should be OK
    let longish = "c".repeat(63);
    assert!(v.validate_tenant_id(&longish).is_ok());
}

#[test]
fn integration_tenant_id_rejects_spoofing_vectors() {
    // These are common attack vectors that should be rejected
    let attack_vectors = [
        "../../etc", // Path traversal
        "admin\n",   // Newline injection
        "default ",  // Trailing space
        "<script>",  // XSS
        "system",    // Reserved (exact)
        "SYSTEM",    // Reserved (case-insensitive)
        "Admin",     // Reserved (mixed case)
    ];
    for attack in &attack_vectors {
        assert!(
            TenantId::new(attack).is_err(),
            "expected attack vector '{attack}' to be rejected"
        );
    }
}

#[test]
fn integration_tenant_id_rejects_empty_and_whitespace() {
    assert!(TenantId::new("").is_err());
    assert!(TenantId::new("   ").is_err());
    assert!(TenantId::new("\t").is_err());
    assert!(TenantId::new("\n").is_err());
}

// =============================================================================
// L18: Anti-spoofing verification (tenant header spoofing mitigation)
// =============================================================================

#[test]
fn integration_anti_spoofing_happy_path() {
    let v = TenantValidation::default();

    // The header-claimed tenant matches the cryptographically verified credential
    assert!(
        v.verify_tenant_identity("tenant-alpha", "tenant-alpha")
            .is_ok()
    );
}

#[test]
fn integration_anti_spoofing_detects_mismatch() {
    let v = TenantValidation::default();

    // An attacker sets X-Tokn-Tenant-ID to a different tenant than their credential
    let err = v
        .verify_tenant_identity("attacker-claimed-tenant", "credential-verified-tenant")
        .unwrap_err();

    match &err {
        TenantError::SpoofAttempt { expected, actual } => {
            assert_eq!(expected.as_str(), "credential-verified-tenant");
            assert_eq!(actual.as_str(), "attacker-claimed-tenant");
        }
        _ => panic!("expected SpoofAttempt error, got: {err}"),
    }

    // Verify the error message is descriptive (audit L4)
    let msg = err.to_string();
    assert!(
        msg.contains("spoofing"),
        "error message should mention spoofing: {msg}"
    );
    assert!(
        msg.contains("credential-verified-tenant"),
        "error message should include expected tenant: {msg}"
    );
    assert!(
        msg.contains("attacker-claimed-tenant"),
        "error message should include actual claim: {msg}"
    );
}

#[test]
fn integration_anti_spoofing_handles_empty_ids() {
    let v = TenantValidation::default();
    let err = v.verify_tenant_identity("", "real-tenant").unwrap_err();
    assert!(matches!(err, TenantError::SpoofAttempt { .. }));
}

// =============================================================================
// L4: Typed error propagation
// =============================================================================

#[test]
fn integration_tenant_error_propagates_through_port_error() {
    use tokenledger::routing::ports::PortError;

    // Demonstrate that TenantError can be converted into PortError::Tenant
    let tenant_err = TenantError::TenantNotFound("missing-tenant".to_string());
    let port_err: PortError = tenant_err.into();

    match port_err {
        PortError::Tenant(inner) => {
            assert!(matches!(inner, TenantError::TenantNotFound(_)));
        }
        _ => panic!("expected PortError::Tenant, got: {port_err}"),
    }
}

#[test]
fn integration_tenant_error_from_operator() {
    use tokenledger::routing::ports::PortError;

    // Test the ? operator conversion
    fn inner() -> Result<(), PortError> {
        Err(TenantError::TenantInactive("disabled-tenant".to_string()))?;
        Ok(())
    }

    let err = inner().unwrap_err();
    match err {
        PortError::Tenant(inner) => {
            assert!(matches!(inner, TenantError::TenantInactive(_)));
            assert_eq!(inner.tenant_id(), Some("disabled-tenant"));
        }
        _ => panic!("expected PortError::Tenant, got: {err}"),
    }
}

#[test]
fn integration_all_tenant_error_variants_have_clear_messages() {
    let errors = vec![
        TenantError::TenantNotFound("x".to_string()),
        TenantError::TenantInactive("y".to_string()),
        TenantError::InvalidTenantId("bad".to_string()),
        TenantError::SpoofAttempt {
            expected: "a".to_string(),
            actual: "b".to_string(),
        },
        TenantError::Unauthorized("z".to_string()),
        TenantError::ResolutionError("db error".to_string()),
    ];

    for err in &errors {
        let msg = err.to_string();
        assert!(!msg.is_empty(), "error message should not be empty");
        assert!(
            msg.len() > 10,
            "error message '{}' should be descriptive",
            msg
        );
    }
}

// =============================================================================
// L22: Tenant resolver (isolation boundary)
// =============================================================================

#[test]
fn integration_tenant_resolver_round_trip() {
    let mut resolver = InMemoryTenantResolver::new();

    let original = TenantContext {
        tenant_id: TenantId::new_unchecked("resolved-tenant"),
        tier: TenantTier::Enterprise,
        key_id: "key-enterprise-001".to_string(),
        features: vec![
            features::AUDIT_LOG.to_string(),
            features::ADVANCED_ROUTING.to_string(),
        ],
    };
    resolver.register(original.clone());

    let rt = tokio::runtime::Runtime::new().unwrap();
    let resolved = rt
        .block_on(resolver.resolve_tenant(&TenantId::new_unchecked("resolved-tenant")))
        .expect("should resolve");

    assert_eq!(resolved.tenant_id.as_str(), original.tenant_id.as_str());
    assert_eq!(resolved.tier, original.tier);
    assert_eq!(resolved.key_id, original.key_id);
    assert_eq!(resolved.features, original.features);
}

#[test]
fn integration_tenant_resolver_not_found() {
    let resolver = InMemoryTenantResolver::new();
    let rt = tokio::runtime::Runtime::new().unwrap();

    let err = rt
        .block_on(resolver.resolve_tenant(&TenantId::new_unchecked("ghost-tenant")))
        .unwrap_err();

    assert!(matches!(err, TenantError::TenantNotFound(_)));
    assert_eq!(err.tenant_id(), Some("ghost-tenant"));
}

#[test]
fn integration_tenant_resolver_isolation() {
    // Verify that tenant A cannot access tenant B's data
    let mut resolver = InMemoryTenantResolver::new();

    let tenant_a = TenantContext {
        tenant_id: TenantId::new_unchecked("tenant-a"),
        tier: TenantTier::Pro,
        key_id: "key-a".to_string(),
        features: vec![],
    };
    let tenant_b = TenantContext {
        tenant_id: TenantId::new_unchecked("tenant-b"),
        tier: TenantTier::Free,
        key_id: "key-b".to_string(),
        features: vec![],
    };
    resolver.register(tenant_a);
    resolver.register(tenant_b);

    let rt = tokio::runtime::Runtime::new().unwrap();

    // Tenant B tries to access tenant A's context
    let err = rt
        .block_on(resolver.resolve_tenant(&TenantId::new_unchecked("TENANT-A")))
        .unwrap_err();
    // The resolver is case-sensitive - "TENANT-A" != "tenant-a"
    assert!(matches!(err, TenantError::TenantNotFound(_)));
}

// =============================================================================
// L6: Tenant config defaults
// =============================================================================

#[test]
fn integration_rate_limit_config_defaults() {
    let cfg = RateLimitConfig::default();
    assert_eq!(cfg.requests_per_minute, 60);
    assert_eq!(cfg.tokens_per_minute, 100_000);
    assert!((cfg.burst_multiplier - 2.0).abs() < f64::EPSILON);
}

// =============================================================================
// Tenant tier integration (L22)
// =============================================================================

#[test]
fn integration_tenant_tier_enterprise_can_do_everything() {
    assert!(TenantTier::Enterprise.encompasses(&TenantTier::Free));
    assert!(TenantTier::Enterprise.encompasses(&TenantTier::Pro));
    assert!(TenantTier::Enterprise.encompasses(&TenantTier::Enterprise));
}

#[test]
fn integration_tenant_tier_free_cannot_access_pro_or_enterprise() {
    assert!(TenantTier::Free.encompasses(&TenantTier::Free));
    assert!(!TenantTier::Free.encompasses(&TenantTier::Pro));
    assert!(!TenantTier::Free.encompasses(&TenantTier::Enterprise));
}

// =============================================================================
// Tenant context serialization round-trip
// =============================================================================

#[test]
fn integration_tenant_context_serde_roundtrip() {
    let ctx = TenantContext {
        tenant_id: TenantId::new_unchecked("serde-test-tenant"),
        tier: TenantTier::Pro,
        key_id: "serde-key-42".to_string(),
        features: vec![features::AUDIT_LOG.to_string()],
    };

    let json = serde_json::to_string_pretty(&ctx).expect("serialize tenant context");
    let deserialized: TenantContext =
        serde_json::from_str(&json).expect("deserialize tenant context");

    assert_eq!(deserialized.tenant_id.as_str(), "serde-test-tenant");
    assert_eq!(deserialized.tier, TenantTier::Pro);
    assert_eq!(deserialized.key_id, "serde-key-42");
    assert!(deserialized.has_feature(features::AUDIT_LOG));
}
