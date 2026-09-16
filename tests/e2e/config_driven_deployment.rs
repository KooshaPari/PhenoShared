//! End-to-end test: config-driven deployment pipeline.
//!
//! Tests the full path from loading pheno-config, deriving NvmsConfig
//! for each tier, creating instances through the driver, verifying
//! properties, and confirming state is observable through JSON
//! serialization.

#[test]
fn config_to_deployment_pipeline() {
    // ── Phase 1: Load config (no file → uses defaults) ─────────────
    let pheno_cfg = pheno_config::PhenoConfig::load()
        .expect("E2E: config load should succeed");

    // Verify defaults are sane
    assert!(!pheno_cfg.nvms.version.is_empty());
    assert!(!pheno_cfg.nvms.platform.is_empty());
    assert!(pheno_cfg.sandbox.startup_ms_wasm > 0);
    assert!(pheno_cfg.sandbox.startup_ms_gvisor > pheno_cfg.sandbox.startup_ms_wasm);
    assert!(pheno_cfg.sandbox.startup_ms_firecracker > pheno_cfg.sandbox.startup_ms_gvisor);

    // ── Phase 2: Build NvmsConfigs from pheno_cfg ──────────────────
    use pheno_compose_driver::NvmsConfig;

    let wasm_config = NvmsConfig::wasm("deploy-wasm")
        .with_memory_gb(2)
        .with_env("DEPLOY_MODE", "e2e");

    let gvisor_config = NvmsConfig::gvisor("deploy-gvisor")
        .with_cpus(4)
        .with_memory_gb(8)
        .with_network("prod-net");

    let fc_config = NvmsConfig::firecracker_with("deploy-fc", &pheno_cfg)
        .with_cpus(8)
        .with_memory_gb(16)
        .with_image("ubuntu:22.04")
        .with_env("ENV", "production")
        .with_env("LOG_LEVEL", "info");

    // Verify configs reflect the pheno_cfg defaults where applicable
    assert_eq!(
        fc_config.cpu_count,
        Some(pheno_cfg.driver.firecracker_default_cpus + 6), // overridden to 8
    );
    assert_eq!(
        fc_config.memory_bytes,
        Some(16 * 1024 * 1024 * 1024),
    );

    // ── Phase 3: Initialize driver ─────────────────────────────────
    let driver = pheno_compose_driver::NvmsDriver::new()
        .expect("E2E: driver init");

    // ── Phase 4: Create instances from configs ─────────────────────
    let mut wasm_inst = driver
        .create_instance_with_config(&wasm_config)
        .expect("E2E: create wasm");
    let mut gvisor_inst = driver
        .create_instance_with_config(&gvisor_config)
        .expect("E2E: create gvisor");
    let mut fc_inst = driver
        .create_instance_with_config(&fc_config)
        .expect("E2E: create firecracker");

    // ── Phase 5: Verify properties match configs ───────────────────
    assert_eq!(wasm_inst.name(), "deploy-wasm");
    assert_eq!(wasm_inst.tier(), pheno_compose_driver::Tier::Wasm);
    assert!(wasm_inst.is_running());

    assert_eq!(gvisor_inst.name(), "deploy-gvisor");
    assert_eq!(gvisor_inst.tier(), pheno_compose_driver::Tier::Gvisor);
    assert!(gvisor_inst.is_running());

    assert_eq!(fc_inst.name(), "deploy-fc");
    assert_eq!(fc_inst.tier(), pheno_compose_driver::Tier::Firecracker);
    assert!(fc_inst.is_running());

    // ── Phase 6: Exercise lifecycle on each instance ────────────────
    for (inst, label) in [
        (&mut wasm_inst, "wasm"),
        (&mut gvisor_inst, "gvisor"),
        (&mut fc_inst, "fc"),
    ] {
        inst.stop().expect(&format!("E2E: stop {label}"));
        assert!(
            !inst.is_running(),
            "E2E: {label} should be stopped after stop()"
        );

        inst.start().expect(&format!("E2E: restart {label}"));
        assert!(
            inst.is_running(),
            "E2E: {label} should be running after start()"
        );
    }

    // ── Phase 7: Verify health check after deployments ─────────────
    let report = pheno_compose_driver::health::check();
    assert!(
        report.healthy,
        "E2E: health check failed with active deployments: {}",
        report.message
    );

    // ── Phase 8: Serialize health + config and verify ──────────────
    let report_json = serde_json::to_string(&report).expect("E2E: serialize health");
    assert!(report_json.contains("\"healthy\":true"));
    assert!(report_json.contains("\"probes\""));

    let config_json = serde_json::to_string(&pheno_cfg).expect("E2E: serialize config");
    let restored_cfg: pheno_config::PhenoConfig =
        serde_json::from_str(&config_json).expect("E2E: deserialize config");
    assert_eq!(
        restored_cfg.gpu.memory_bytes,
        pheno_cfg.gpu.memory_bytes,
    );

    // ── Phase 9: Teardown ──────────────────────────────────────────
    drop(wasm_inst);
    drop(gvisor_inst);
    drop(fc_inst);

    // ── Phase 10: Post-teardown health ─────────────────────────────
    let post = pheno_compose_driver::health::check();
    assert!(
        post.healthy,
        "E2E: post-teardown health check failed: {}",
        post.message
    );

    eprintln!("E2E: config-driven deployment pipeline completed successfully");
}
