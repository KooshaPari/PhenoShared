//! Integration tests: FFI ↔ Driver type bridge.
//!
//! Verifies that types roundtrip correctly between the `nvms-ffi` C
//! bindings and the high-level `pheno-compose-driver` API.

/// Tier enum values must be preserved across the FFI boundary.
#[test]
fn tier_ffi_roundtrip_all_variants() {
    use nvms_ffi::Tier as FfiTier;
    use pheno_compose_driver::Tier;

    let pairs = [
        (Tier::Wasm, FfiTier::Wasm),
        (Tier::Gvisor, FfiTier::Gvisor),
        (Tier::Firecracker, FfiTier::Firecracker),
    ];

    for (driver_tier, ffi_tier) in &pairs {
        // Driver → FFI
        let converted_ffi: FfiTier = (*driver_tier).into();
        assert_eq!(converted_ffi, *ffi_tier, "driver→ffi failed for {driver_tier:?}");

        // FFI → Driver
        let converted_back: Tier = converted_ffi.into();
        assert_eq!(converted_back, *driver_tier, "ffi→driver failed for {ffi_tier:?}");
    }
}

/// Status enum values must be preserved across the FFI boundary.
#[test]
fn status_ffi_roundtrip_all_variants() {
    use nvms_ffi::Status as FfiStatus;
    use pheno_compose_driver::InstanceStatus;

    let pairs = [
        (InstanceStatus::Stopped, FfiStatus::Stopped),
        (InstanceStatus::Starting, FfiStatus::Starting),
        (InstanceStatus::Running, FfiStatus::Running),
        (InstanceStatus::Stopping, FfiStatus::Stopping),
        (InstanceStatus::Error, FfiStatus::Error),
    ];

    for (driver_status, ffi_status) in &pairs {
        let converted_back: InstanceStatus = (*ffi_status).into();
        assert_eq!(converted_back, *driver_status);
    }
}

/// Driver-level instance and FFI-level instance must agree on tier and
/// name when both refer to the same underlying resource.
#[test]
fn driver_instance_matches_ffi_instance_tier_and_name() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    for (tier, name) in [
        (pheno_compose_driver::Tier::Wasm, "bridge-wasm"),
        (pheno_compose_driver::Tier::Gvisor, "bridge-gvisor"),
        (pheno_compose_driver::Tier::Firecracker, "bridge-fc"),
    ] {
        let inst = driver
            .create_instance(tier, name)
            .unwrap_or_else(|e| panic!("create {name}: {e}"));

        assert_eq!(inst.tier(), tier, "tier mismatch for {name}");
        assert_eq!(inst.name(), name, "name mismatch for {name}");
        assert!(inst.is_running(), "new instance should be running");
    }
}

/// The driver version string must match what `nvms_ffi::version()` returns.
#[test]
fn driver_version_matches_ffi_version() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");
    assert_eq!(
        driver.version(),
        nvms_ffi::version(),
        "driver and FFI should report the same version"
    );
}

/// Creating an instance through the driver should assign a unique,
/// positive ID each time.
#[test]
fn instance_ids_are_unique_and_positive() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    let mut ids = std::collections::HashSet::new();
    for i in 0..10 {
        let inst = driver
            .create_instance(
                pheno_compose_driver::Tier::Wasm,
                &format!("id-test-{i}"),
            )
            .expect("create instance");
        let id = inst.id();
        assert!(id > 0, "ID should be positive, got {id}");
        assert!(ids.insert(id), "duplicate ID detected: {id}");
    }
}
