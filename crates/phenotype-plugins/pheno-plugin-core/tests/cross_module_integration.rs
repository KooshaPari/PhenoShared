//! Cross-module integration tests for `pheno-plugin-core`.
//!
//! These tests live in `tests/` (i.e. an external integration test crate),
//! so they consume the crate **exactly as a downstream user would**. They
//! guard against:
//!
//! - Silent removal of public items (compile-time check in
//!   `test_re_exports_compile`).
//! - Regressions in the `#[from]` error conversions from `std::io::Error`
//!   and `serde_json::Error`.
//! - Regressions in the `#[serde(default)]` behavior of `PluginConfig`.
//! - The independence of the VCS and storage adapter slots on a fresh
//!   `PluginRegistry`.
//!
//! All references are to the **public** API — no `pub(crate)` items are
//! touched. If something in this file stops compiling, the public surface
//! of `pheno-plugin-core` has changed in a way that downstream consumers
//! would also feel.

use std::error::Error as StdError;

use pheno_plugin_core::error::PluginResult;
use pheno_plugin_core::registry::RegistryStats;
use pheno_plugin_core::traits::{
    ConflictInfo, FeatureArtifacts, MergeResult, PluginConfig, WorktreeInfo,
};
use pheno_plugin_core::{AdapterPlugin, PluginError, PluginRegistry, StoragePlugin, VcsPlugin};

// =============================================================================
// 1. Error roundtrips for the `#[from]` conversions
// =============================================================================

#[test]
fn test_error_roundtrip_io() {
    // Build a real `std::io::Error` and let `Into<PluginError>` drive the
    // conversion. This exercises the `#[from] std::io::Error` arm.
    let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "io_payload");
    let err: PluginError = io_err.into();

    // The `Display` impl is derived from `thiserror` and must be non-empty.
    let displayed = format!("{}", err);
    assert!(
        !displayed.is_empty(),
        "PluginError::Io Display should not be empty"
    );

    // `std::error::Error::source` must yield the original io error.
    let src = StdError::source(&err);
    assert!(
        src.is_some(),
        "PluginError::Io must preserve the original io::Error via source()"
    );
}

#[test]
fn test_error_roundtrip_serde() {
    // Build a real `serde_json::Error` from malformed JSON.
    let bad: serde_json::Error = serde_json::from_str::<i32>("{ not valid json").unwrap_err();
    let err: PluginError = bad.into();

    // Display is non-empty.
    let displayed = format!("{}", err);
    assert!(
        !displayed.is_empty(),
        "PluginError::Serialization Display should not be empty"
    );

    // Source preserved through the `#[from] serde_json::Error` arm.
    assert!(
        StdError::source(&err).is_some(),
        "PluginError::Serialization must preserve the original serde_json::Error via source()"
    );
}

// =============================================================================
// 2. `PluginConfig` serde behavior
// =============================================================================

#[test]
fn test_plugin_config_default_adapter_config_in_json() {
    // JSON payload intentionally omits `adapter_config` to exercise
    // `#[serde(default)]` on the field.
    let json_str = r#"{"name":"x","version":"1.0"}"#;
    let cfg: PluginConfig = serde_json::from_str(json_str).expect("deserialize should succeed");

    assert_eq!(cfg.name, "x");
    assert_eq!(cfg.version, "1.0");
    assert!(
        cfg.adapter_config.is_null(),
        "adapter_config should default to Null when omitted, got: {}",
        cfg.adapter_config
    );

    // Round-trip: serialize back and verify the JSON explicitly contains
    // `"adapter_config":null` (the `#[serde(default)]` behavior surfaces
    // a real null on the wire, not just a missing key).
    let serialized = serde_json::to_string(&cfg).expect("serialize should succeed");
    let value: serde_json::Value =
        serde_json::from_str(&serialized).expect("serialized output should be valid JSON");

    assert!(
        value.get("adapter_config").is_some(),
        "serialized JSON must include `adapter_config` key, got: {}",
        serialized
    );
    assert!(
        value["adapter_config"].is_null(),
        "serialized `adapter_config` must be null, got: {}",
        serialized
    );
}

#[test]
fn test_plugin_config_full_serde_roundtrip() {
    let original = PluginConfig {
        name: "git".to_string(),
        version: "0.1.0".to_string(),
        adapter_config: serde_json::json!({"k": "v"}),
    };

    // Serialize → deserialize and check all three fields are preserved.
    let serialized = serde_json::to_string(&original).expect("serialize should succeed");
    let deserialized: PluginConfig =
        serde_json::from_str(&serialized).expect("deserialize should succeed");

    assert_eq!(deserialized.name, original.name);
    assert_eq!(deserialized.version, original.version);
    assert_eq!(deserialized.adapter_config, original.adapter_config);
}

// =============================================================================
// 3. `PluginRegistry`: VCS and storage slots are independent
// =============================================================================

#[test]
fn test_registry_vcs_and_storage_independent() {
    // No real plugins registered — we just need the accessors to behave
    // sensibly on a fresh registry.
    let registry = PluginRegistry::new();

    assert_eq!(
        registry.vcs_adapters(),
        Vec::<String>::new(),
        "vcs_adapters() should be empty on a fresh registry"
    );
    assert_eq!(
        registry.storage_adapters(),
        Vec::<String>::new(),
        "storage_adapters() should be empty on a fresh registry"
    );
    assert!(
        registry.vcs("any").is_none(),
        "vcs(\"any\") should be None on a fresh registry"
    );
    assert!(
        registry.storage("any").is_none(),
        "storage(\"any\") should be None on a fresh registry"
    );
    assert!(
        !registry.is_finalized(),
        "a fresh registry should not be finalized"
    );
}

#[test]
fn test_registry_default_trait_works() {
    let from_new = PluginRegistry::new();
    let from_default = PluginRegistry::default();

    // Both should be unfinalized.
    assert!(!from_new.is_finalized());
    assert!(!from_default.is_finalized());

    // Both should report empty adapter lists.
    assert!(from_new.vcs_adapters().is_empty());
    assert!(from_new.storage_adapters().is_empty());
    assert!(from_default.vcs_adapters().is_empty());
    assert!(from_default.storage_adapters().is_empty());

    // Both should report zero counts in `stats()`.
    let s_new = from_new.stats();
    let s_default = from_default.stats();
    assert_eq!(s_new.vcs_count, 0);
    assert_eq!(s_new.storage_count, 0);
    assert_eq!(s_default.vcs_count, 0);
    assert_eq!(s_default.storage_count, 0);
}

#[test]
fn test_registry_stats_format() {
    let registry = PluginRegistry::new();
    let stats = registry.stats();

    // The three documented fields are accessible and have expected values.
    assert_eq!(stats.vcs_count, 0);
    assert_eq!(stats.storage_count, 0);
    assert!(!stats.finalized);

    // `RegistryStats` derives `Debug` and is publicly accessible — make
    // sure the formatting is stable enough to include all field names.
    let debug_repr = format!("{:?}", stats);
    assert!(
        !debug_repr.is_empty(),
        "RegistryStats Debug output should not be empty"
    );
    assert!(
        debug_repr.contains("vcs_count"),
        "RegistryStats Debug output should mention `vcs_count`: {}",
        debug_repr
    );
    assert!(
        debug_repr.contains("storage_count"),
        "RegistryStats Debug output should mention `storage_count`: {}",
        debug_repr
    );
    assert!(
        debug_repr.contains("finalized"),
        "RegistryStats Debug output should mention `finalized`: {}",
        debug_repr
    );
}

// =============================================================================
// 4. `PluginResult` type alias
// =============================================================================

#[test]
fn test_plugin_result_ok_typed() {
    // The alias is `Result<T, PluginError>` — confirm it works for three
    // distinct payload types.
    let r_i64: PluginResult<i64> = Ok(42);
    assert_eq!(r_i64.unwrap(), 42);

    let r_string: PluginResult<String> = Ok("x".to_string());
    assert_eq!(r_string.unwrap(), "x");

    let r_unit: PluginResult<()> = Ok(());
    assert!(r_unit.is_ok());
}

// =============================================================================
// 5. `Display` impls for representative `PluginError` variants
// =============================================================================

#[test]
fn test_plugin_error_display_variants() {
    // Three of the ten variants: Initialization, NotFound, Validation.
    // For each, Display must be non-empty and must contain the inner string.
    let cases: Vec<(PluginError, &str, &str)> = vec![
        (
            PluginError::Initialization("init_payload".to_string()),
            "init_payload",
            "initialization",
        ),
        (
            PluginError::NotFound("notfound_payload".to_string()),
            "notfound_payload",
            "not found",
        ),
        (
            PluginError::Validation("val_payload".to_string()),
            "val_payload",
            "validation",
        ),
    ];

    for (err, payload, keyword) in cases {
        let displayed = format!("{}", err);
        let lower = displayed.to_lowercase();

        assert!(
            !displayed.is_empty(),
            "Display for {:?} should be non-empty",
            err
        );
        assert!(
            displayed.contains(payload),
            "Display for {:?} missing inner payload `{}`: `{}`",
            err,
            payload,
            displayed
        );
        assert!(
            lower.contains(keyword),
            "Display for {:?} missing keyword `{}`: `{}`",
            err,
            keyword,
            displayed
        );
    }
}

// =============================================================================
// 6. Re-exports at the crate root compile
// =============================================================================

#[test]
fn test_re_exports_compile() {
    // The `let _: Option<X> = None;` lines below force the compiler to
    // resolve every public type and trait alias. If any name disappears
    // from the public surface, this test stops compiling — which is the
    // whole point of an external integration test for re-exports.
    //
    // For trait objects, `Box<dyn Trait>` is required to satisfy the
    // implicit `Sized` bound on `Option<T>`'s parameter.

    // Traits (re-exported at the crate root).
    let _: Option<Box<dyn AdapterPlugin>> = None;
    let _: Option<Box<dyn VcsPlugin>> = None;
    let _: Option<Box<dyn StoragePlugin>> = None;

    // Core error and registry types (re-exported at the crate root).
    let _: Option<PluginError> = None;
    let _: Option<PluginRegistry> = None;

    // Types that live in the `traits` sub-module — also part of the public
    // surface, accessed from outside the crate here.
    let _: Option<PluginConfig> = None;
    let _: Option<WorktreeInfo> = None;
    let _: Option<MergeResult> = None;
    let _: Option<ConflictInfo> = None;
    let _: Option<FeatureArtifacts> = None;

    // Type alias from the `error` sub-module.
    let _: Option<PluginResult<()>> = None;

    // Struct from the `registry` sub-module.
    let _: Option<RegistryStats> = None;
}
