//! End-to-end test: full system bootstrap, exercise, and teardown.
//!
//! This test exercises the complete NVMS stack from driver initialization
//! through health checking, instance creation across all tiers, lifecycle
//! management, performance stats, and finally graceful teardown. It acts
//! as a smoke test for the entire system.

#[test]
fn full_system_bootstrap_exercise_teardown() {
    // ── Phase 1: Bootstrap ─────────────────────────────────────────
    let driver = pheno_compose_driver::NvmsDriver::new()
        .expect("E2E: driver initialization should succeed");

    let version = driver.version();
    assert!(
        version.starts_with("1.0"),
        "E2E: unexpected NVMS version: {version}"
    );

    // ── Phase 2: Health check ──────────────────────────────────────
    let report = pheno_compose_driver::health::check();
    assert!(
        report.healthy,
        "E2E: system health check failed: {}",
        report.message
    );
    assert_eq!(report.version, version);
    assert!(
        report.platform.contains('/'),
        "E2E: platform should contain '/': {}",
        report.platform
    );
    assert!(
        report.check_duration_ms < 5_000,
        "E2E: health check too slow ({}ms)",
        report.check_duration_ms
    );

    // ── Phase 3: Create instances across all tiers ─────────────────
    let mut instances: Vec<(
        pheno_compose_driver::Tier,
        String,
        pheno_compose_driver::Instance,
    )> = Vec::new();

    for (tier, name) in [
        (pheno_compose_driver::Tier::Wasm, "e2e-wasm-1"),
        (pheno_compose_driver::Tier::Wasm, "e2e-wasm-2"),
        (pheno_compose_driver::Tier::Gvisor, "e2e-gvisor-1"),
        (pheno_compose_driver::Tier::Firecracker, "e2e-fc-1"),
    ] {
        let inst = driver
            .create_instance(tier, name)
            .unwrap_or_else(|e| panic!("E2E: create {name}: {e}"));

        assert!(inst.is_running(), "E2E: {name} should start as Running");
        assert_eq!(inst.tier(), tier, "E2E: {name} tier mismatch");
        assert_eq!(inst.name(), name, "E2E: {name} name mismatch");
        assert!(inst.id() > 0, "E2E: {name} should have positive ID");
        assert!(inst.estimated_startup_ms() > 0, "E2E: {name} startup estimate should be > 0");

        instances.push((tier, name.to_owned(), inst));
    }

    // ── Phase 4: Exercise lifecycle on a Wasm instance ─────────────
    // Find the first wasm instance
    let wasm_idx = instances
        .iter()
        .position(|(t, _, _)| *t == pheno_compose_driver::Tier::Wasm)
        .expect("E2E: should have a wasm instance");

    let (_, ref _wasm_name, ref mut wasm_inst) = instances[wasm_idx];

    // Stop
    wasm_inst.stop().expect("E2E: stop wasm");
    assert_eq!(wasm_inst.status(), pheno_compose_driver::InstanceStatus::Stopped);

    // Start again
    wasm_inst.start().expect("E2E: restart wasm");
    assert_eq!(wasm_inst.status(), pheno_compose_driver::InstanceStatus::Running);

    // Stop again before teardown
    wasm_inst.stop().expect("E2E: final stop wasm");
    assert_eq!(wasm_inst.status(), pheno_compose_driver::InstanceStatus::Stopped);

    // ── Phase 5: Verify FFI perf stats are accessible ──────────────
    let stats = nvms_ffi::perf_stats();
    assert!(stats.startup_time_ns > 0, "E2E: perf startup time should be > 0");
    assert!(stats.memory_used_bytes > 0, "E2E: perf memory should be > 0");
    assert!(stats.gpu_utilization >= 0.0, "E2E: GPU util should be >= 0");

    // ── Phase 6: Verify GPU info is accessible ─────────────────────
    let gpu = nvms_ffi::gpu_info();
    assert!(!gpu.name.is_empty(), "E2E: GPU name should not be empty");
    assert!(gpu.compute_units > 0, "E2E: compute units should be > 0");

    // ── Phase 7: Verify config deserialization works ───────────────
    let default_config = pheno_config::PhenoConfig::default();
    let json = serde_json::to_string(&default_config).expect("E2E: serialize config");
    let restored: pheno_config::PhenoConfig =
        serde_json::from_str(&json).expect("E2E: deserialize config");
    assert_eq!(
        restored.sandbox.max_sandbox_id_len,
        default_config.sandbox.max_sandbox_id_len
    );

    // ── Phase 8: Teardown (drop all instances) ─────────────────────
    let count = instances.len();
    drop(instances);

    // ── Phase 9: Verify health after teardown ──────────────────────
    let post_report = pheno_compose_driver::health::check();
    assert!(
        post_report.healthy,
        "E2E: health check failed after teardown: {}",
        post_report.message
    );

    // ── Phase 10: Summary ──────────────────────────────────────────
    eprintln!("E2E: successfully exercised {count} instances across all tiers");
    eprintln!("E2E: health check duration = {}ms", post_report.check_duration_ms);
}
