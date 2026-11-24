//! Integration tests: instance lifecycle through the driver API.
//!
//! Tests full start → stop → restart cycles and status transitions.

/// Full lifecycle: create → running → stop → stopped → start → running.
#[test]
fn full_instance_lifecycle_start_stop_restart() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");
    let mut inst = driver
        .create_instance(pheno_compose_driver::Tier::Wasm, "lifecycle-full")
        .expect("create instance");

    assert_eq!(inst.status(), pheno_compose_driver::InstanceStatus::Running);

    // Stop
    inst.stop().expect("stop");
    assert_eq!(inst.status(), pheno_compose_driver::InstanceStatus::Stopped);
    assert!(!inst.is_running());

    // Start again
    inst.start().expect("restart");
    assert_eq!(inst.status(), pheno_compose_driver::InstanceStatus::Running);
    assert!(inst.is_running());

    // Stop again
    inst.stop().expect("second stop");
    assert_eq!(inst.status(), pheno_compose_driver::InstanceStatus::Stopped);
}

/// Each tier must produce instances with the correct tier tag.
#[test]
fn all_tiers_produce_correct_instance_tier() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    let tiers = [
        (pheno_compose_driver::Tier::Wasm, "tier-w"),
        (pheno_compose_driver::Tier::Gvisor, "tier-g"),
        (pheno_compose_driver::Tier::Firecracker, "tier-fc"),
    ];

    for (tier, name) in &tiers {
        let inst = driver
            .create_instance(*tier, name)
            .unwrap_or_else(|e| panic!("create {name}: {e}"));
        assert_eq!(inst.tier(), *tier, "tier mismatch for {name}");
    }
}

/// Dropping an instance must not panic (the Drop impl calls destroy).
#[test]
fn instance_drop_does_not_panic() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    // Create and immediately drop 5 instances
    for i in 0..5 {
        let _inst = driver
            .create_instance(
                pheno_compose_driver::Tier::Wasm,
                &format!("drop-test-{i}"),
            )
            .expect("create instance");
        // instance is dropped here at end of scope
    }
}

/// Multiple instances can coexist and be managed independently.
#[test]
fn multiple_instances_are_independent() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    let mut inst_a = driver
        .create_instance(pheno_compose_driver::Tier::Wasm, "indep-a")
        .expect("create a");
    let mut inst_b = driver
        .create_instance(pheno_compose_driver::Tier::Gvisor, "indep-b")
        .expect("create b");

    // Stop A — B should still be running
    inst_a.stop().expect("stop a");
    assert_eq!(inst_a.status(), pheno_compose_driver::InstanceStatus::Stopped);
    assert_eq!(inst_b.status(), pheno_compose_driver::InstanceStatus::Running);

    // Stop B — A should still be stopped
    inst_b.stop().expect("stop b");
    assert_eq!(inst_a.status(), pheno_compose_driver::InstanceStatus::Stopped);
    assert_eq!(inst_b.status(), pheno_compose_driver::InstanceStatus::Stopped);

    // Start A — B should still be stopped
    inst_a.start().expect("start a");
    assert_eq!(inst_a.status(), pheno_compose_driver::InstanceStatus::Running);
    assert_eq!(inst_b.status(), pheno_compose_driver::InstanceStatus::Stopped);
}

/// Estimated startup times must be tier-ordered correctly:
/// Wasm < gVisor < Firecracker.
#[test]
fn estimated_startup_times_are_tier_ordered() {
    let driver = pheno_compose_driver::NvmsDriver::new().expect("driver init");

    let inst_w = driver
        .create_instance(pheno_compose_driver::Tier::Wasm, "est-w")
        .unwrap();
    let inst_g = driver
        .create_instance(pheno_compose_driver::Tier::Gvisor, "est-g")
        .unwrap();
    let inst_f = driver
        .create_instance(pheno_compose_driver::Tier::Firecracker, "est-fc")
        .unwrap();

    let wasm_ms = inst_w.estimated_startup_ms();
    let gvisor_ms = inst_g.estimated_startup_ms();
    let fc_ms = inst_f.estimated_startup_ms();

    assert!(
        wasm_ms < gvisor_ms,
        "wasm ({wasm_ms}ms) should be faster than gvisor ({gvisor_ms}ms)"
    );
    assert!(
        gvisor_ms < fc_ms,
        "gvisor ({gvisor_ms}ms) should be faster than firecracker ({fc_ms}ms)"
    );
}
