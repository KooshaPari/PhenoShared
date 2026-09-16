//! Hardening integration tests for `pheno-plugin-core`.
//!
//! These tests exercise the *interaction* between the new hardening
//! modules ([`manifest`], [`guardrails`], [`lifecycle`],
//! [`capabilities`]) and the existing public surface. They live in
//! `tests/` so they consume the crate exactly as a downstream user
//! would.
//!
//! What is covered:
//!
//! - End-to-end manifest construction: builder → validate → use.
//! - Guardrail constants and the manifest → guardrail wiring.
//! - Lifecycle state machine: allowed/forbidden transitions.
//! - Public re-exports for the hardening types.
//! - Capability declaration checks against an SDK manifest.
//!
//! References use the **public** API only. If a public name moves,
//! these tests fail to compile — which is the goal.
//!
//! [`manifest`]: pheno_plugin_core::manifest
//! [`guardrails`]: pheno_plugin_core::guardrails
//! [`lifecycle`]: pheno_plugin_core::lifecycle
//! [`capabilities`]: pheno_plugin_core::capabilities

use pheno_plugin_core::manifest::PluginKind;
use pheno_plugin_core::{
    guardrails, Capability, PluginError, PluginKind as RePluginKind, PluginManifest, PluginState,
};

// =============================================================================
// 1. Public surface — hardening types are reachable from the crate root
// =============================================================================

#[test]
fn test_hardening_re_exports_compile() {
    // The re-exports at the crate root are the contract downstream
    // users code against. Pinning them here means a public-API
    // regression in the hardening surface fails CI before a release.

    // Re-exported type aliases / structs.
    let _: Option<PluginManifest> = None;
    let _: Option<RePluginKind> = None;
    let _: Option<PluginState> = None;
    let _: Option<Capability> = None;

    // Re-exported errors must still be reachable.
    let _: Option<PluginError> = None;
}

#[test]
fn test_hardening_submodule_paths_compile() {
    // Beyond the re-exports, the modules themselves must stay public so
    // downstream code can reach items the re-exports don't surface
    // (e.g. constants in `guardrails`).
    use pheno_plugin_core::capabilities;
    use pheno_plugin_core::guardrails as g;
    use pheno_plugin_core::lifecycle;
    use pheno_plugin_core::manifest;

    // Touch each module to force name resolution.
    let _: Option<capabilities::Capability> = None;
    let _: Option<lifecycle::PluginState> = None;
    let _: Option<manifest::PluginManifest> = None;
    let _: Option<manifest::PluginKind> = None;

    // Constant from `guardrails` — pinned at the public boundary.
    let _: usize = g::MAX_PLUGIN_NAME_LEN;
    let _: usize = g::MAX_SEMVER_LEN;
    let _: usize = g::MAX_DEPENDENCIES;
    let _: usize = g::MAX_CAPABILITIES;
}

// =============================================================================
// 2. Manifest ↔ guardrail wiring
// =============================================================================

#[test]
fn test_manifest_validation_calls_guardrails() {
    // The manifest's `validate()` should fail with the same class of
    // error as the underlying guardrail when the name is invalid. This
    // pins the delegation contract.
    let err = PluginManifest::new("Bad Name!", "0.1.0", PluginKind::Vcs)
        .expect_err("constructor should reject bad name");
    let msg = err.to_string();
    // Validation errors come from `guardrails::validate_plugin_name`.
    assert!(
        msg.contains("Bad Name") || msg.contains("illegal character"),
        "expected validation message to mention the bad name, got: {}",
        msg
    );
    assert!(
        matches!(err, PluginError::Validation(_)),
        "expected Validation variant, got: {:?}",
        err
    );
}

#[test]
fn test_manifest_rejects_invalid_version_via_guardrail() {
    let err = PluginManifest::new("ok", "v1.2.3-not-semver", PluginKind::Vcs)
        .expect_err("constructor should reject bad version");
    assert!(matches!(err, PluginError::Validation(_)));
}

#[test]
fn test_manifest_round_trip_then_re_validate() {
    // Build → validate → serialize → deserialize → re-validate. All
    // should succeed.
    let original = PluginManifest::new("git", "0.1.0", PluginKind::Vcs)
        .unwrap()
        .with_description("Git adapter".to_string())
        .with_capabilities(vec![Capability::WorkingTree])
        .with_min_host_version("0.1.0".to_string())
        .with_depends_on(vec!["pheno-plugin-core".to_string()]);

    let json = serde_json::to_string(&original).unwrap();
    let parsed: PluginManifest = serde_json::from_str(&json).unwrap();
    assert!(parsed.validate().is_ok(), "re-validation must succeed");

    // And the guardrails agree independently.
    assert!(guardrails::validate_plugin_name(&parsed.name).is_ok());
    assert!(guardrails::validate_semver(&parsed.version).is_ok());
    assert!(guardrails::validate_dependencies(&parsed.depends_on).is_ok());
    assert!(guardrails::validate_capabilities(&parsed.capabilities).is_ok());
}

#[test]
fn test_manifest_depends_on_self_rejected() {
    // The `with_depends_on` setter is fine, but `validate()` must
    // catch the self-loop. We have to build the manifest with the
    // setter and then validate, because `PluginManifest::new` would
    // already call validate.
    let m = PluginManifest::new("self-loop", "0.1.0", PluginKind::Generic)
        .unwrap()
        .with_depends_on(vec!["self-loop".to_string()]);
    let err = m.validate().expect_err("self-dependency should fail");
    assert!(matches!(err, PluginError::Validation(_)));
    assert!(err.to_string().contains("itself"));
}

#[test]
fn test_manifest_depends_on_reserved_name_rejected() {
    // The reserved-name guardrail must apply transitively to
    // dependencies, not just to the plugin's own name.
    let m = PluginManifest::new("ok", "0.1.0", PluginKind::Generic)
        .unwrap()
        .with_depends_on(vec!["host".to_string()]); // "host" is reserved
    let err = m.validate().expect_err("reserved dep should fail");
    assert!(matches!(err, PluginError::Validation(_)));
}

// =============================================================================
// 3. Capability checks
// =============================================================================

#[test]
fn test_capability_lookups() {
    let m = PluginManifest::new("cap-test", "0.1.0", PluginKind::Vcs)
        .unwrap()
        .with_capabilities(vec![
            Capability::Read,
            Capability::WorkingTree,
            Capability::Audit,
        ]);
    assert!(m.has_capability(Capability::Read));
    assert!(m.has_capability(Capability::WorkingTree));
    assert!(m.has_capability(Capability::Audit));
    assert!(!m.has_capability(Capability::Network));
    assert!(!m.has_capability(Capability::ShellExec));
    assert_eq!(m.capability_count(), 3);
}

#[test]
fn test_capability_strings_round_trip() {
    // Downstream tooling reads `as_str()` and parses via `from_str`;
    // this pins both directions.
    for cap in Capability::ALL {
        let s = cap.as_str();
        let parsed = Capability::parse(s).unwrap_or_else(|| panic!("no parse for {}", s));
        assert_eq!(parsed, *cap);
    }
}

#[test]
fn test_capability_kind_matches_manifest() {
    // VCS plugins are typically going to claim WorkingTree; storage
    // plugins are typically going to claim Storage. This test pins
    // *no policy* — it just exercises the wiring between the two
    // surfaces.
    let v = PluginManifest::new("v", "0.1.0", PluginKind::Vcs)
        .unwrap()
        .with_capabilities(vec![Capability::WorkingTree]);
    let s = PluginManifest::new("s", "0.1.0", PluginKind::Storage)
        .unwrap()
        .with_capabilities(vec![Capability::Storage]);
    assert_eq!(v.kind, PluginKind::Vcs);
    assert_eq!(s.kind, PluginKind::Storage);
    assert!(v.has_capability(Capability::WorkingTree));
    assert!(s.has_capability(Capability::Storage));
}

#[test]
fn test_capability_unknown_string_returns_none() {
    // Pin the failure mode of `from_str` for unknown identifiers.
    assert!(Capability::parse("nope").is_none());
    assert!(Capability::parse("").is_none());
    assert!(Capability::parse("READ").is_none()); // case-sensitive
}

// =============================================================================
// 4. Lifecycle state machine
// =============================================================================

#[test]
fn test_lifecycle_happy_path() {
    let mut s = PluginState::Registered;
    s = s.transition(PluginState::Initialized).unwrap();
    s = s.transition(PluginState::Running).unwrap();
    s = s.transition(PluginState::Stopped).unwrap();
    assert!(s.is_terminal());
}

#[test]
fn test_lifecycle_failure_recovery() {
    // `Failed` is terminal but recoverable: it can transition back to
    // `Registered` for a manual reset.
    let mut s = PluginState::Registered;
    s = s.transition(PluginState::Failed).unwrap();
    assert!(s.is_terminal());
    s = s.transition(PluginState::Registered).unwrap();
    assert_eq!(s, PluginState::Registered);
}

#[test]
fn test_lifecycle_illegal_transitions_blocked() {
    // Skipping `Initialized` is illegal.
    let err = PluginState::Registered.transition(PluginState::Running);
    assert!(err.is_err());

    // Going backwards is illegal.
    let err = PluginState::Running.transition(PluginState::Initialized);
    assert!(err.is_err());

    // Re-stopping is illegal (Stopped is terminal).
    let err = PluginState::Stopped.transition(PluginState::Stopped);
    assert!(err.is_err());
}

#[test]
fn test_lifecycle_state_strings() {
    // Stable string identifiers are part of the observability surface
    // (logs, error messages, telemetry). Pin them.
    assert_eq!(PluginState::Registered.as_str(), "registered");
    assert_eq!(PluginState::Initialized.as_str(), "initialized");
    assert_eq!(PluginState::Running.as_str(), "running");
    assert_eq!(PluginState::Stopped.as_str(), "stopped");
    assert_eq!(PluginState::Failed.as_str(), "failed");
}

#[test]
fn test_lifecycle_can_transition_predicate_matches_transition_method() {
    // `can_transition_to` and `transition` must agree: if the predicate
    // is true, the method succeeds; if false, the method fails.
    use PluginState::*;
    for &a in &[Registered, Initialized, Running, Stopped, Failed] {
        for &b in &[Registered, Initialized, Running, Stopped, Failed] {
            let can = a.can_transition_to(b);
            let method_result = a.transition(b).is_ok();
            assert_eq!(
                can,
                method_result,
                "predicate/method mismatch for {} -> {}",
                a.as_str(),
                b.as_str()
            );
        }
    }
}

// =============================================================================
// 5. Cross-cutting: building a "host" workflow from public types
// =============================================================================

#[test]
fn test_host_workflow_rejects_bad_manifest_before_registering() {
    // A host should: (1) read a manifest, (2) validate it via the
    // public API, (3) only then register a plugin. The guardrails
    // must catch every common mistake *before* the registry is
    // touched.

    // Bad: reserved name.
    let raw = r#"{"name":"core","version":"0.1.0","kind":"vcs"}"#;
    let parsed: PluginManifest = serde_json::from_str(raw).unwrap();
    assert!(parsed.validate().is_err());

    // Bad: bad version.
    let raw = r#"{"name":"good","version":"garbage","kind":"vcs"}"#;
    let parsed: PluginManifest = serde_json::from_str(raw).unwrap();
    assert!(parsed.validate().is_err());

    // Bad: bad name (uppercase).
    let raw = r#"{"name":"BadName","version":"0.1.0","kind":"vcs"}"#;
    let parsed: PluginManifest = serde_json::from_str(raw).unwrap();
    assert!(parsed.validate().is_err());

    // Good: every field valid.
    let raw = r#"{"name":"ok","version":"0.1.0","kind":"vcs"}"#;
    let parsed: PluginManifest = serde_json::from_str(raw).unwrap();
    assert!(parsed.validate().is_ok());
}

#[test]
fn test_guardrail_constants_are_above_zero() {
    // The constants are part of the public API; their values are
    // load-bearing. Pin them at sane minima.
    assert!(guardrails::MAX_PLUGIN_NAME_LEN >= 8);
    assert!(guardrails::MAX_SEMVER_LEN >= 8);
    assert!(guardrails::MAX_DEPENDENCIES >= 1);
    assert!(guardrails::MAX_CAPABILITIES >= 1);
    // Reserved-name list is documented as non-empty.
    assert!(!guardrails::RESERVED_PLUGIN_NAMES.is_empty());
}

#[test]
fn test_reserved_names_all_rejected() {
    // The reserved-name list is the public contract: every name in
    // it must be rejected by `validate_plugin_name`. A regression
    // that lets a reserved name through would defeat the guard.
    for name in guardrails::RESERVED_PLUGIN_NAMES {
        let result = guardrails::validate_plugin_name(name);
        assert!(
            result.is_err(),
            "expected reserved name '{}' to be rejected",
            name
        );
    }
}

#[test]
fn test_full_manifest_builder_path() {
    // Exercise the *entire* builder surface in one test so a missing
    // setter (e.g. `with_min_host_version`) gets caught at compile
    // time, not at runtime.
    let m = PluginManifest::new("pheno-plugin-bundle", "1.2.3", PluginKind::Vcs)
        .expect("constructor should succeed")
        .with_description("A test manifest exercising every setter".to_string())
        .with_capabilities(vec![
            Capability::Read,
            Capability::FilesystemRead,
            Capability::FilesystemWrite,
            Capability::WorkingTree,
        ])
        .with_min_host_version("0.5.0".to_string())
        .with_depends_on(vec!["pheno-plugin-core".to_string()]);

    // Builder values made it through.
    assert_eq!(m.description, "A test manifest exercising every setter");
    assert_eq!(m.capability_count(), 4);
    assert_eq!(m.min_host_version.as_deref(), Some("0.5.0"));
    assert_eq!(m.depends_on, vec!["pheno-plugin-core".to_string()]);

    // And the result is valid.
    assert!(m.validate().is_ok());
}
