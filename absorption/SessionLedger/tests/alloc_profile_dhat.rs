//! L8 alloc-profile smoke: `dhat` heap statistics over `process_session`.
//!
//! Built only with `--features alloc-profile`. Companion to the counting-allocator
//! smoke (`tests/allocation_budget.rs`); does not enable jemalloc or daemon profiling.
//!
//! Run:
//!   `cargo test --test alloc_profile_dhat --features alloc-profile --locked`
//!   `pwsh ./scripts/alloc-profile-check.ps1`

use std::path::PathBuf;

use dhat::{Alloc, HeapStats, Profiler};
use session_ledger::domain::session::{Corpus, Message, Role, Session};

#[global_allocator]
static GLOBAL: Alloc = Alloc;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn load_profile() -> (u64, u64) {
    let path = repo_root().join("docs/ops/alloc-profile.json");
    let raw = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let value: serde_json::Value = serde_json::from_str(&raw)
        .unwrap_or_else(|error| panic!("parse {}: {error}", path.display()));

    let max_bytes = value
        .get("max_bytes_ceiling")
        .and_then(serde_json::Value::as_u64)
        .expect("max_bytes_ceiling must be a positive integer");
    let total_blocks = value
        .get("total_blocks_ceiling")
        .and_then(serde_json::Value::as_u64)
        .expect("total_blocks_ceiling must be a positive integer");
    (max_bytes, total_blocks)
}

fn sample_session() -> Session {
    let mut session = Session::new("alloc-profile-001", Corpus::Forge);
    session.title = Some("Allocator profile fixture".into());
    session.messages = vec![
        Message::new(Role::User, "Please summarize the auth timeout fix."),
        Message::new(Role::Assistant, "TTL was hardcoded to 300s; bumping to 1800s."),
        Message::new(Role::User, "Preserve MFA and existing session cookies."),
        Message::new(Role::Assistant, "MFA path unchanged; cookies keep the new TTL."),
        Message::new(Role::User, "Add a regression test for the cookie path."),
        Message::new(Role::Assistant, "Added cookie TTL regression coverage."),
        Message::new(Role::User, "Looks good — ship it."),
        Message::new(Role::Assistant, "Shipped. Follow-up: document the new default."),
    ];
    session
}

#[test]
fn process_session_stays_under_dhat_heap_profile() {
    let (max_bytes_ceiling, total_blocks_ceiling) = load_profile();
    let session = sample_session();

    // Warm once so one-time process/static init is outside the measured window.
    let _warm = session_ledger::process_session(&session);

    let _profiler = Profiler::new_heap();
    let doc = session_ledger::process_session(&session);
    let stats = HeapStats::get();

    assert!(!doc.entities.is_empty() || !doc.source_id.is_empty(), "expected a non-empty OKF doc");

    eprintln!(
        "alloc-profile (dhat): max_bytes={} total_blocks={} (ceilings {} / {})",
        stats.max_bytes, stats.total_blocks, max_bytes_ceiling, total_blocks_ceiling
    );

    assert!(
        stats.max_bytes <= usize::try_from(max_bytes_ceiling).expect("ceiling fits usize"),
        "max_bytes {} exceeds ceiling {}",
        stats.max_bytes,
        max_bytes_ceiling
    );
    assert!(
        stats.total_blocks <= total_blocks_ceiling,
        "total_blocks {} exceeds ceiling {}",
        stats.total_blocks,
        total_blocks_ceiling
    );
}
