use criterion::{black_box, criterion_group, criterion_main, BenchmarkId, Criterion};
use std::sync::Arc;

use pheno_plugin_core::{
    error::{PluginError, PluginResult},
    registry::PluginRegistry,
    traits::{
        AdapterPlugin, ConflictInfo, FeatureArtifacts, MergeResult, StoragePlugin, VcsPlugin,
        WorktreeInfo,
    },
};
use std::path::{Path, PathBuf};

// ---------------------------------------------------------------------------
// Inline no-op mocks — no dependency on test helpers.
// ---------------------------------------------------------------------------

struct NullVcs {
    name: String,
}

impl NullVcs {
    fn new(name: &str) -> Self {
        Self { name: name.to_string() }
    }
}

impl AdapterPlugin for NullVcs {
    fn name(&self) -> &str {
        &self.name
    }
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn initialize(&self, _: pheno_plugin_core::traits::PluginConfig) -> PluginResult<()> {
        Ok(())
    }
}

#[async_trait::async_trait]
impl VcsPlugin for NullVcs {
    async fn create_worktree(&self, _: &str, _: &str) -> PluginResult<PathBuf> {
        Ok(PathBuf::from("/tmp/bench"))
    }
    async fn list_worktrees(&self) -> PluginResult<Vec<WorktreeInfo>> {
        Ok(vec![])
    }
    async fn cleanup_worktree(&self, _: &Path) -> PluginResult<()> {
        Ok(())
    }
    async fn create_branch(&self, _: &str, _: &str) -> PluginResult<()> {
        Ok(())
    }
    async fn checkout_branch(&self, _: &str) -> PluginResult<()> {
        Ok(())
    }
    async fn merge_to_target(&self, _: &str, _: &str) -> PluginResult<MergeResult> {
        Ok(MergeResult { success: true, conflicts: vec![], merged_commit: None })
    }
    async fn detect_conflicts(&self, _: &str, _: &str) -> PluginResult<Vec<ConflictInfo>> {
        Ok(vec![])
    }
    async fn read_artifact(&self, _: &str, _: &str) -> PluginResult<String> {
        Ok(String::new())
    }
    async fn write_artifact(&self, _: &str, _: &str, _: &str) -> PluginResult<()> {
        Ok(())
    }
    async fn artifact_exists(&self, _: &str, _: &str) -> PluginResult<bool> {
        Ok(false)
    }
    async fn scan_feature_artifacts(&self, _: &str) -> PluginResult<FeatureArtifacts> {
        Ok(FeatureArtifacts { meta_json: None, audit_chain: None, evidence_paths: vec![] })
    }
}

struct NullStorage {
    name: String,
}

impl NullStorage {
    fn new(name: &str) -> Self {
        Self { name: name.to_string() }
    }
}

impl AdapterPlugin for NullStorage {
    fn name(&self) -> &str {
        &self.name
    }
    fn version(&self) -> &str {
        "0.1.0"
    }
    fn initialize(&self, _: pheno_plugin_core::traits::PluginConfig) -> PluginResult<()> {
        Ok(())
    }
}

#[async_trait::async_trait]
impl StoragePlugin for NullStorage {
    async fn create_feature(&self, _: &serde_json::Value) -> PluginResult<i64> {
        Ok(1)
    }
    async fn get_feature_by_slug(&self, _: &str) -> PluginResult<Option<serde_json::Value>> {
        Ok(None)
    }
    async fn get_feature_by_id(&self, _: i64) -> PluginResult<Option<serde_json::Value>> {
        Ok(None)
    }
    async fn update_feature_state(&self, _: i64, _: &str) -> PluginResult<()> {
        Ok(())
    }
    async fn list_all_features(&self) -> PluginResult<Vec<serde_json::Value>> {
        Ok(vec![])
    }
    async fn create_work_package(&self, _: &serde_json::Value) -> PluginResult<i64> {
        Ok(1)
    }
    async fn get_work_package(&self, _: i64) -> PluginResult<Option<serde_json::Value>> {
        Ok(None)
    }
    async fn update_wp_state(&self, _: i64, _: &str) -> PluginResult<()> {
        Ok(())
    }
    async fn append_audit_entry(&self, _: &serde_json::Value) -> PluginResult<i64> {
        Ok(1)
    }
    async fn get_audit_trail(&self, _: i64) -> PluginResult<Vec<serde_json::Value>> {
        Ok(vec![])
    }
}

// ---------------------------------------------------------------------------
// Benchmarks
// ---------------------------------------------------------------------------

/// How long does it take to build a registry with N VCS plugins?
/// Informal budget: 100 registrations < 1 ms.
fn bench_registry_register_vcs(c: &mut Criterion) {
    let mut group = c.benchmark_group("registry/register_vcs");
    for n in [1usize, 10, 50, 100] {
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, &n| {
            b.iter(|| {
                let registry = PluginRegistry::new();
                for i in 0..n {
                    let plugin = Box::new(NullVcs::new(&format!("vcs-{}", i)));
                    registry.register_vcs(black_box(plugin)).unwrap();
                }
                black_box(registry.stats())
            });
        });
    }
    group.finish();
}

/// Lookup speed on a pre-populated registry.
/// Informal budget: single lookup from 100-plugin registry < 200 ns.
fn bench_registry_lookup(c: &mut Criterion) {
    let mut group = c.benchmark_group("registry/lookup");
    for n in [10usize, 50, 100] {
        let registry = Arc::new(PluginRegistry::new());
        for i in 0..n {
            registry.register_vcs(Box::new(NullVcs::new(&format!("vcs-{}", i)))).unwrap();
        }
        let target = format!("vcs-{}", n / 2);
        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, _| {
            b.iter(|| {
                black_box(registry.vcs(black_box(&target)));
            });
        });
    }
    group.finish();
}

/// Registry stats across both plugin kinds.
fn bench_registry_stats(c: &mut Criterion) {
    let registry = PluginRegistry::new();
    for i in 0..50 {
        registry.register_vcs(Box::new(NullVcs::new(&format!("vcs-{}", i)))).unwrap();
        registry.register_storage(Box::new(NullStorage::new(&format!("storage-{}", i)))).unwrap();
    }
    c.bench_function("registry/stats_100_plugins", |b| {
        b.iter(|| black_box(registry.stats()));
    });
}

/// Error code dispatch — should be zero-allocation.
fn bench_error_code(c: &mut Criterion) {
    let errors: Vec<PluginError> = vec![
        PluginError::Initialization("x".into()),
        PluginError::NotFound("x".into()),
        PluginError::AlreadyRegistered("x".into()),
        PluginError::Operation("x".into()),
        PluginError::Validation("x".into()),
    ];
    c.bench_function("error/code_dispatch", |b| {
        b.iter(|| {
            for e in &errors {
                black_box(e.code());
                black_box(e.recovery_hint());
            }
        });
    });
}

criterion_group!(
    benches,
    bench_registry_register_vcs,
    bench_registry_lookup,
    bench_registry_stats,
    bench_error_code,
);
criterion_main!(benches);
