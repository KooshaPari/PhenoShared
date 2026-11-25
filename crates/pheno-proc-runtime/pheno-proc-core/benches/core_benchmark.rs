//! Benchmarks for pheno-proc-core
//!
//! Measures ProjectResources, SharedRuntime, and ProcessPool operations.

use criterion::{criterion_group, criterion_main, Criterion};
use pheno_proc_core::*;

fn bench_project_resources(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();

    c.bench_function("project_resources_set_get", |b| {
        b.iter(|| {
            rt.block_on(async {
                let resources = ProjectResources::new();
                for i in 0..100 {
                    resources
                        .set_limits(
                            &format!("project-{i}"),
                            ProjectLimits {
                                memory_limit_mb: 4096,
                                max_processes: 10,
                                cpu_affinity: None,
                            },
                        )
                        .await;
                }
                for i in 0..100 {
                    let _ = resources.get_limits(&format!("project-{i}")).await;
                }
            });
        });
    });

    c.bench_function("project_resources_check_limits", |b| {
        b.iter(|| {
            rt.block_on(async {
                let resources = ProjectResources::new();
                resources
                    .set_limits(
                        "test",
                        ProjectLimits {
                            memory_limit_mb: 4096,
                            max_processes: 10,
                            cpu_affinity: None,
                        },
                    )
                    .await;
                for _ in 0..100 {
                    let _ = resources.check_limits("test").await.unwrap();
                }
            });
        });
    });
}

fn bench_shared_runtime(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();

    c.bench_function("shared_runtime_status", |b| {
        b.iter(|| {
            rt.block_on(async {
                let runtime = SharedRuntime::new(4);
                for _ in 0..100 {
                    let _ = runtime.status().await;
                }
            });
        });
    });

    c.bench_function("shared_runtime_health_check", |b| {
        b.iter(|| {
            rt.block_on(async {
                let runtime = SharedRuntime::new(4);
                for _ in 0..100 {
                    let _ = runtime.health_check().await;
                }
            });
        });
    });
}

fn bench_process_status(c: &mut Criterion) {
    c.bench_function("process_status_display", |b| {
        b.iter(|| {
            let _ = ProcessStatus::Running.to_string();
            let _ = ProcessStatus::Stopped.to_string();
            let _ = ProcessStatus::Exited.to_string();
            let _ = ProcessStatus::Error.to_string();
        });
    });
}

criterion_group!(
    benches,
    bench_project_resources,
    bench_shared_runtime,
    bench_process_status
);
criterion_main!(benches);
