//! Integration tests: health monitoring pipeline.
//!
//! Verifies that the health-check subsystem exercises the full
//! init → version → platform pipeline and reports correctly.

/// Health check must return a report with all probes passing.
#[test]
fn health_check_all_probes_pass() {
    let report = pheno_compose_driver::health::check();
    assert!(report.healthy, "health check should pass: {}", report.message);
    assert!(!report.probes.is_empty(), "should have at least one probe");

    for probe in &report.probes {
        assert!(probe.ok, "probe '{}' should pass: {:?}", probe.name, probe.error);
        assert!(
            probe.error.is_none(),
            "passing probe should not have error: {:?}",
            probe.error
        );
    }
}

/// Health report must contain version and platform from the FFI layer.
#[test]
fn health_report_contains_ffi_version_and_platform() {
    let report = pheno_compose_driver::health::check();
    assert_eq!(report.version, nvms_ffi::version());
    assert_eq!(report.platform, nvms_ffi::platform_info());
}

/// Health report must be JSON-serializable and deserializable.
#[test]
fn health_report_json_roundtrip() {
    let report = pheno_compose_driver::health::check();
    let json = serde_json::to_string_pretty(&report).expect("serialize");
    let restored: pheno_compose_driver::health::HealthReport =
        serde_json::from_str(&json).expect("deserialize");

    assert_eq!(restored.healthy, report.healthy);
    assert_eq!(restored.version, report.version);
    assert_eq!(restored.platform, report.platform);
    assert_eq!(restored.probes.len(), report.probes.len());
    for (a, b) in restored.probes.iter().zip(report.probes.iter()) {
        assert_eq!(a.name, b.name);
        assert_eq!(a.ok, b.ok);
    }
}

/// Health check must complete in a reasonable amount of time (< 5s).
#[test]
fn health_check_completes_quickly() {
    let report = pheno_compose_driver::health::check();
    assert!(
        report.check_duration_ms < 5_000,
        "health check took {}ms, expected < 5000ms",
        report.check_duration_ms
    );
}

/// After creating and destroying instances, the health check should
/// still pass (no resource leaks affecting the FFI layer).
#[test]
fn health_check_passes_after_instance_churn() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    // Create and immediately drop several instances
    for i in 0..20 {
        let _inst = driver
            .create_instance(
                pheno_compose_driver::Tier::Wasm,
                &format!("churn-{i}"),
            )
            .expect("create");
    }

    // Health check must still pass
    let report = pheno_compose_driver::health::check();
    assert!(
        report.healthy,
        "health check failed after instance churn: {}",
        report.message
    );
}
