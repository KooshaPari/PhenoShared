//! Integration tests for pheno-proc-core
//!
//! Tests ProcessPool, SharedRuntime, and ProjectResources in realistic scenarios.

use pheno_proc_core::*;

// ---------------------------------------------------------------------------
// ProcessStatus display and conversion
// ---------------------------------------------------------------------------

#[test]
fn test_process_status_display() {
    assert_eq!(ProcessStatus::Running.to_string(), "running");
    assert_eq!(ProcessStatus::Stopped.to_string(), "stopped");
    assert_eq!(ProcessStatus::Exited.to_string(), "exited");
    assert_eq!(ProcessStatus::Error.to_string(), "error");
}

// ---------------------------------------------------------------------------
// ProjectResources: set/get/check limits
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_project_resources_default_limits() {
    let resources = ProjectResources::new();
    let limits = resources.get_limits("nonexistent").await;

    // Defaults: 4096 MB memory, 10 processes
    assert_eq!(limits.memory_limit_mb, 4096);
    assert_eq!(limits.max_processes, 10);
    assert!(limits.cpu_affinity.is_none());
}

#[tokio::test]
async fn test_project_resources_set_and_get() {
    let resources = ProjectResources::new();

    let custom = ProjectLimits {
        memory_limit_mb: 8192,
        max_processes: 20,
        cpu_affinity: Some(vec![0, 1]),
    };

    resources.set_limits("my-project", custom.clone()).await;
    let retrieved = resources.get_limits("my-project").await;

    assert_eq!(retrieved.memory_limit_mb, 8192);
    assert_eq!(retrieved.max_processes, 20);
    assert_eq!(retrieved.cpu_affinity, Some(vec![0, 1]));
}

#[tokio::test]
async fn test_project_resources_check_limits() {
    let resources = ProjectResources::new();

    resources
        .set_limits(
            "proj",
            ProjectLimits {
                memory_limit_mb: 2048,
                max_processes: 5,
                cpu_affinity: None,
            },
        )
        .await;

    let check = resources.check_limits("proj").await.unwrap();
    assert_eq!(check.memory_limit_mb, 2048);
    assert_eq!(check.max_processes, 5);
    assert!(check.overall_ok());
}

#[tokio::test]
async fn test_project_resources_multiple_projects() {
    let resources = ProjectResources::new();

    resources
        .set_limits(
            "alpha",
            ProjectLimits {
                memory_limit_mb: 1024,
                max_processes: 2,
                cpu_affinity: None,
            },
        )
        .await;
    resources
        .set_limits(
            "beta",
            ProjectLimits {
                memory_limit_mb: 4096,
                max_processes: 8,
                cpu_affinity: None,
            },
        )
        .await;

    let alpha = resources.get_limits("alpha").await;
    let beta = resources.get_limits("beta").await;
    assert_eq!(alpha.memory_limit_mb, 1024);
    assert_eq!(beta.memory_limit_mb, 4096);
}

// ---------------------------------------------------------------------------
// SharedRuntime
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_shared_runtime_new() {
    let runtime = SharedRuntime::new(4);
    assert_eq!(runtime.max_per_type, 4);
    let status = runtime.status().await;
    assert_eq!(status.node_total, 0);
    assert_eq!(status.node_idle, 4);
    assert_eq!(status.bun_total, 0);
    assert_eq!(status.bun_idle, 4);
}

#[tokio::test]
async fn test_shared_runtime_status() {
    let runtime = SharedRuntime::new(8);
    let status = runtime.status().await;
    assert_eq!(status.max_per_type, 8);
    assert_eq!(status.node_total, 0);
    assert_eq!(status.node_idle, 8);
    assert_eq!(status.bun_idle, 8);
}

#[tokio::test]
async fn test_shared_runtime_health_check() {
    let runtime = SharedRuntime::new(4);
    let health = runtime.health_check().await;
    assert!(health.healthy);
    assert!(health.issues.is_empty());
}

#[tokio::test]
async fn test_shared_runtime_run_with_pool() {
    let runtime = SharedRuntime::new(4);
    // Use a valid harness type ("node" or "bun") and a command that exits quickly
    let result = runtime
        .run_with_pool("node", "my-project", "--version")
        .await;
    // The command may fail if "node" is not installed, so we just verify the pool logic
    match result {
        Ok((pid, msg)) => {
            assert!(pid > 0);
            assert!(msg.contains("node"));
            assert!(msg.contains("my-project"));
        }
        Err(e) => {
            // "node" binary not found is acceptable in CI
            let err_str = e.to_string();
            assert!(
                err_str.contains("No such file") || err_str.contains("os error"),
                "Unexpected error: {err_str}"
            );
        }
    }
}

#[tokio::test]
async fn test_shared_runtime_run_with_pool_bad_type() {
    let runtime = SharedRuntime::new(4);
    let result = runtime
        .run_with_pool("claude", "my-project", "echo hello")
        .await;
    assert!(result.is_err());
    let err = result.unwrap_err().to_string();
    assert!(err.contains("unknown harness type"));
}

#[tokio::test]
async fn test_shared_runtime_run_with_pool_at_capacity() {
    let runtime = SharedRuntime::new(1);
    // Use a long-running command to fill the single slot
    if let Ok((_, _)) = runtime
        .run_with_pool("node", "proj", "-e \"setTimeout(() => {}, 60000)\"")
        .await
    {
        // Second call should fail if node is available
        let result = runtime.run_with_pool("node", "proj2", "--version").await;
        if let Err(e) = result {
            let err = e.to_string();
            assert!(
                err.contains("at capacity"),
                "Expected capacity error: {err}"
            );
        }
    }
    // Give background task a moment to reclaim
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
}

// ---------------------------------------------------------------------------
// ProcessPool
// ---------------------------------------------------------------------------

#[test]
fn test_process_pool_new() {
    let pool = ProcessPool::new();
    assert_eq!(pool.max_memory_mb, 4096);
    assert_eq!(pool.max_processes, 100);
    assert_eq!(pool.count(), 0);
}

#[test]
fn test_process_pool_with_limits() {
    let pool = ProcessPool::with_limits(8192, 50);
    assert_eq!(pool.max_memory_mb, 8192);
    assert_eq!(pool.max_processes, 50);
}

// ---------------------------------------------------------------------------
// ProjectLimitCheck
// ---------------------------------------------------------------------------

#[test]
fn test_project_limit_check_overall_ok() {
    let check = ProjectLimitCheck {
        memory_mb: 100,
        memory_limit_mb: 4096,
        memory_ok: true,
        process_count: 2,
        max_processes: 10,
        processes_ok: true,
    };
    assert!(check.overall_ok());
}

#[test]
fn test_project_limit_check_memory_over() {
    let check = ProjectLimitCheck {
        memory_mb: 5000,
        memory_limit_mb: 4096,
        memory_ok: false,
        process_count: 2,
        max_processes: 10,
        processes_ok: true,
    };
    assert!(!check.overall_ok());
}

#[test]
fn test_project_limit_check_processes_over() {
    let check = ProjectLimitCheck {
        memory_mb: 100,
        memory_limit_mb: 4096,
        memory_ok: true,
        process_count: 15,
        max_processes: 10,
        processes_ok: false,
    };
    assert!(!check.overall_ok());
}

// ---------------------------------------------------------------------------
// PoolStatus and HealthStatus
// ---------------------------------------------------------------------------

#[test]
fn test_pool_status_fields() {
    let status = PoolStatus {
        node_total: 5,
        node_idle: 3,
        bun_total: 2,
        bun_idle: 1,
        max_per_type: 10,
    };
    assert_eq!(status.node_total, 5);
    assert_eq!(status.node_idle, 3);
    assert_eq!(status.bun_total, 2);
    assert_eq!(status.bun_idle, 1);
}

#[test]
fn test_health_status_fields() {
    let health = HealthStatus {
        healthy: true,
        issues: vec!["warn: high mem".to_string()],
        node_in_use: 2,
        bun_in_use: 1,
    };
    assert!(health.healthy);
    assert_eq!(health.issues.len(), 1);
    assert_eq!(health.node_in_use, 2);
}

// ---------------------------------------------------------------------------
// ProcessFilter
// ---------------------------------------------------------------------------

#[test]
fn test_process_filter_variants() {
    let _all = ProcessFilter::All;
    let _by_project = ProcessFilter::ByProject("test".to_string());
    let _by_harness = ProcessFilter::ByHarness("codex".to_string());
    // Ensure these compile and can be constructed
}
