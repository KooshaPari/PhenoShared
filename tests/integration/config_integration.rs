//! Integration tests: config → driver → instance creation.
//!
//! Verifies that `pheno-config` defaults flow correctly through
//! `NvmsConfig` into `pheno-compose-driver` instance creation.

/// `NvmsConfig::firecracker()` must pull default CPU and memory values
/// from the workspace `pheno_config::PhenoConfig` defaults.
#[test]
fn firecracker_config_inherits_pheno_config_defaults() {
    use pheno_compose_driver::NvmsConfig;

    let config = NvmsConfig::firecracker("fc-defaults");
    let defaults = pheno_config::PhenoConfig::default();

    assert_eq!(
        config.cpu_count,
        Some(defaults.driver.firecracker_default_cpus),
        "CPU count should come from pheno_config"
    );
    assert_eq!(
        config.memory_bytes,
        Some(defaults.driver.firecracker_default_memory_bytes),
        "memory should come from pheno_config"
    );
}

/// Builder chain must accumulate multiple overrides correctly.
#[test]
fn config_builder_chains_multiple_overrides() {
    use pheno_compose_driver::NvmsConfig;

    let config = NvmsConfig::gvisor("multi-override")
        .with_cpus(16)
        .with_memory_gb(32)
        .with_network("isolated-net")
        .with_image("alpine:3.19")
        .with_env("LOG_LEVEL", "debug")
        .with_env("RUST_LOG", "trace");

    assert_eq!(config.name, "multi-override");
    assert_eq!(config.cpu_count, Some(16));
    assert_eq!(config.memory_bytes, Some(32 * 1024 * 1024 * 1024));
    assert_eq!(config.network.as_deref(), Some("isolated-net"));
    assert_eq!(config.image.as_deref(), Some("alpine:3.19"));
    assert_eq!(config.env.len(), 2);
    assert_eq!(config.env[0].key, "LOG_LEVEL");
    assert_eq!(config.env[1].value, "trace");
}

/// `create_instance_with_config` must produce an instance whose tier
/// and name match the supplied config.
#[test]
fn create_instance_with_config_matches_tier_and_name() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    let configs = [
        (pheno_compose_driver::NvmsConfig::wasm("cfg-w"), "cfg-w"),
        (pheno_compose_driver::NvmsConfig::gvisor("cfg-g"), "cfg-g"),
        (pheno_compose_driver::NvmsConfig::firecracker("cfg-fc"), "cfg-fc"),
    ];

    for (config, expected_name) in &configs {
        let inst = driver
            .create_instance_with_config(config)
            .unwrap_or_else(|e| panic!("create with config {expected_name}: {e}"));
        assert_eq!(inst.name(), *expected_name);
        assert!(inst.is_running());
    }
}

/// `with_memory_gb` must convert gigabytes to bytes correctly.
#[test]
fn memory_gb_conversion_is_exact() {
    use pheno_compose_driver::NvmsConfig;

    let config = NvmsConfig::wasm("mem-test").with_memory_gb(8);
    assert_eq!(config.memory_bytes, Some(8 * 1024 * 1024 * 1024));

    let config = NvmsConfig::wasm("mem-zero").with_memory_gb(0);
    assert_eq!(config.memory_bytes, Some(0));

    let config = NvmsConfig::wasm("mem-large").with_memory_gb(64);
    assert_eq!(config.memory_bytes, Some(64 * 1024 * 1024 * 1024));
}

/// `NvmsConfig::wasm` and `NvmsConfig::gvisor` must not pre-fill
/// cpu/memory defaults (they're only set by `firecracker`).
#[test]
fn non_firecracker_configs_have_no_resource_defaults() {
    use pheno_compose_driver::NvmsConfig;

    let wasm = NvmsConfig::wasm("no-res");
    assert!(wasm.cpu_count.is_none(), "wasm should not default CPUs");
    assert!(wasm.memory_bytes.is_none(), "wasm should not default memory");

    let gvisor = NvmsConfig::gvisor("no-res");
    assert!(gvisor.cpu_count.is_none(), "gvisor should not default CPUs");
    assert!(gvisor.memory_bytes.is_none(), "gvisor should not default memory");
}
