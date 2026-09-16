//! Cross-crate integration tests for the phenotype-infra monorepo.
//!
//! These tests verify that the major crates (`nvms-ffi`, `pheno-compose-driver`,
//! `pheno-config`) can be linked together and that their basic public API
//! contracts hold.

// ---------------------------------------------------------------------------
// nvms-ffi integration
// ---------------------------------------------------------------------------

#[test]
fn nvms_ffi_version_and_platform() {
    let version = nvms_ffi::version();
    assert!(!version.is_empty(), "version should not be empty");
    assert!(
        version.starts_with("1.0"),
        "version should start with 1.0, got: {version}"
    );

    let platform = nvms_ffi::platform_info();
    assert!(!platform.is_empty(), "platform should not be empty");
    assert!(platform.contains('/'), "platform should contain '/', got: {platform}");
}

#[test]
fn nvms_ffi_init_and_gpu_info() {
    // init should succeed (shim returns 0)
    assert!(nvms_ffi::init().is_ok());

    let info = nvms_ffi::gpu_info();
    assert!(!info.name.is_empty());
    assert!(info.compute_units > 0);
}

#[test]
fn nvms_ffi_instance_lifecycle() {
    nvms_ffi::init().unwrap();
    let inst = unsafe { nvms_ffi::Instance::create(nvms_ffi::Tier::Wasm, "integ-test") }
        .expect("instance creation should succeed");
    assert_eq!(inst.tier(), nvms_ffi::Tier::Wasm);
    assert_eq!(inst.status(), nvms_ffi::Status::Running);

    inst.stop().unwrap();
    assert_eq!(inst.status(), nvms_ffi::Status::Stopped);
}

// ---------------------------------------------------------------------------
// pheno-compose-driver integration
// ---------------------------------------------------------------------------

#[test]
fn pheno_compose_driver_initialization() {
    use pheno_compose_driver::NvmsDriver;

    let driver = NvmsDriver::new().expect("driver init should succeed");
    assert!(
        driver.version().starts_with("1.0"),
        "unexpected version: {}",
        driver.version()
    );
}

#[test]
fn pheno_compose_driver_create_and_lifecycle() {
    use pheno_compose_driver::{InstanceStatus, NvmsDriver, Tier};

    let driver = NvmsDriver::new().unwrap();
    let mut inst = driver
        .create_instance(Tier::Wasm, "integ-wasm")
        .expect("create instance");
    assert_eq!(inst.tier(), Tier::Wasm);
    assert_eq!(inst.status(), InstanceStatus::Running);
    assert_ne!(inst.id(), 0);

    inst.stop().unwrap();
    assert_eq!(inst.status(), InstanceStatus::Stopped);

    inst.start().unwrap();
    assert_eq!(inst.status(), InstanceStatus::Running);
}

#[test]
fn pheno_compose_driver_multiple_tiers() {
    use pheno_compose_driver::{NvmsDriver, Tier};

    let driver = NvmsDriver::new().unwrap();

    for (tier, name) in [
        (Tier::Wasm, "multi-wasm"),
        (Tier::Gvisor, "multi-gvisor"),
        (Tier::Firecracker, "multi-fc"),
    ] {
        let inst = driver
            .create_instance(tier, name)
            .unwrap_or_else(|e| panic!("create {name}: {e}"));
        assert_eq!(inst.tier(), tier);
        assert_eq!(inst.name(), name);
    }
}

#[test]
fn pheno_compose_driver_with_config() {
    use pheno_compose_driver::{NvmsConfig, NvmsDriver};

    let driver = NvmsDriver::new().unwrap();
    let config = NvmsConfig::wasm("cfg-wasm").with_cpus(2).with_memory_gb(1);
    let inst = driver
        .create_instance_with_config(&config)
        .expect("create with config");
    assert_eq!(inst.name(), "cfg-wasm");
}

// ---------------------------------------------------------------------------
// Health check integration
// ---------------------------------------------------------------------------

#[test]
fn health_check_returns_report() {
    let report = pheno_compose_driver::health::check();
    assert!(report.healthy, "health check should pass: {}", report.message);
    assert!(!report.version.is_empty());
    assert!(!report.platform.is_empty());
    assert!(!report.probes.is_empty());
    assert!(
        report.probes.iter().all(|p| p.ok),
        "all probes should pass: {:?}",
        report.probes
    );
}

#[test]
fn health_report_serialization_roundtrip() {
    let report = pheno_compose_driver::health::check();
    let json = serde_json::to_string_pretty(&report).expect("serialize");
    let _deserialized: pheno_compose_driver::health::HealthReport =
        serde_json::from_str(&json).expect("deserialize");
}

// ---------------------------------------------------------------------------
// Error type integration
// ---------------------------------------------------------------------------

#[test]
fn error_type_conversion_from_ffi() {
    use pheno_compose_driver::errors::Error;

    let ffi_err = nvms_ffi::NvmsError::InitFailed;
    let err: Error = ffi_err.into();
    let msg = err.to_string();
    assert!(msg.contains("NVMS"), "message should reference NVMS: {msg}");
}

#[test]
fn error_type_display_formatting() {
    use pheno_compose_driver::errors::Error;

    let cases = [
        (Error::InitFailed("test".into()), "NVMS initialization failed: test"),
        (Error::CreateFailed("null".into()), "instance creation failed: null"),
        (Error::AppleSiliconNotSupported, "Apple Silicon platform is not supported on this host"),
        (Error::UnsupportedPlatform, "no supported platform backend found"),
    ];
    for (err, expected) in &cases {
        assert_eq!(err.to_string(), *expected, "unexpected display for {err:?}");
    }
}

// ---------------------------------------------------------------------------
// pheno-config integration
// ---------------------------------------------------------------------------

#[test]
fn pheno_config_defaults_are_sensible() {
    let config = pheno_config::PhenoConfig::default();
    assert!(
        config.sandbox.startup_ms_wasm > 0,
        "wasm startup should be > 0"
    );
    assert!(
        config.sandbox.startup_ms_firecracker > config.sandbox.startup_ms_wasm,
        "firecracker should be slower than wasm"
    );
}
