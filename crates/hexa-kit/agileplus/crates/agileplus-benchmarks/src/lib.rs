//! AgilePlus performance benchmarks.
//!
//! This crate contains Criterion benchmarks for all major subsystems:
//! - T116: Event append throughput (SQLite WAL, sequential appends)
//! - T117: Event replay and snapshot rebuild performance
//! - T118: API response time benchmarks (in-process handler calls)
//! - T119: Sync vector / round-trip operations
//! - T120: Graph query performance (in-memory backend)
//!
//! ## Layout
//!
//! - [`helpers`] — sync test-data builders (events, features, sync payloads,
//!   snapshots) shared by every bench file.
//! - `benches/*.rs` — Criterion `[[bench]]` targets, each one a focused
//!   micro-benchmark of a single subsystem.

pub mod helpers;

#[cfg(test)]
mod tests {
    use super::helpers::{
        CountingAggregate, SyncPayload, make_events, make_events_multi_entity, make_feature,
        make_features, make_snapshot, make_sync_payloads, simulate_sync_roundtrip,
    };

    #[test]
    fn crate_compiles_and_exposes_helpers() {
        // Smoke test: ensure the lib surface is wired up and helpers can be
        // called in a single place (also exercises the `pub mod helpers`
        // re-export from benches).
        let _events = make_events(1);
        let _multi = make_events_multi_entity(1, 1);
        let _feature = make_feature(1);
        let _features = make_features(1);
        let _snapshot = make_snapshot(1, 1);
        let _payloads = make_sync_payloads(1);
        let _payload = SyncPayload::new(1);
        let _agg = CountingAggregate::default();

        let p = SyncPayload::new(42);
        let out = simulate_sync_roundtrip(&p);
        assert_eq!(out.id, 42);
    }

    /// Verifies that the optional `sqlite-bench` feature exposes the
    /// in-memory adapter helper. Skipped when the feature is off (which is
    /// the default — the bench targets are disabled in the Cargo.toml).
    #[cfg(feature = "sqlite-bench")]
    #[test]
    fn sqlite_bench_feature_exposes_adapter() {
        let _adapter = super::helpers::make_in_memory_adapter();
    }
}
