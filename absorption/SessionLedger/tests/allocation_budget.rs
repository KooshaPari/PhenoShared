//! L8 allocation-budget smoke: counting-allocator region over `process_session`.
//!
//! Companion to the RSS ingest smoke (`tests/memory_budget.rs` / #196). This is
//! score-1 evidence only — it catches gross heap regressions without enabling
//! jemalloc or continuous `dhat` profiling in production builds.
//!
//! Run:
//!   `cargo test --test allocation_budget --locked`
//!   `pwsh ./scripts/allocation-budget-check.ps1 -SelfCheck`
//!   `pwsh ./scripts/allocation-budget-check.ps1`

use std::alloc::System;
use std::path::PathBuf;
use std::process::Command;

use session_ledger::domain::session::{Corpus, Message, Role, Session};
use stats_alloc::{Region, StatsAlloc, INSTRUMENTED_SYSTEM};

#[global_allocator]
static GLOBAL: &StatsAlloc<System> = &INSTRUMENTED_SYSTEM;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn load_budget() -> (u64, u64) {
    let path = repo_root().join("docs/ops/allocation-budget.json");
    let raw = std::fs::read_to_string(&path)
        .unwrap_or_else(|error| panic!("read {}: {error}", path.display()));
    let value: serde_json::Value = serde_json::from_str(&raw)
        .unwrap_or_else(|error| panic!("parse {}: {error}", path.display()));

    assert_eq!(
        value.get("schema").and_then(serde_json::Value::as_str),
        Some("sessionledger.allocation-budget.v1")
    );

    let bytes = value
        .get("bytes_allocated_ceiling")
        .and_then(serde_json::Value::as_u64)
        .expect("bytes_allocated_ceiling must be a positive integer");
    let allocs = value
        .get("allocations_ceiling")
        .and_then(serde_json::Value::as_u64)
        .expect("allocations_ceiling must be a positive integer");

    assert!(bytes > 0, "bytes_allocated_ceiling must be positive");
    assert!(allocs > 0, "allocations_ceiling must be positive");
    (bytes, allocs)
}

fn sample_session() -> Session {
    let mut session = Session::new("alloc-budget-001", Corpus::Forge);
    session.title = Some("Allocation budget fixture".into());
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
fn allocation_budget_config_exposes_positive_ceilings() {
    let (bytes, allocs) = load_budget();
    assert!(
        bytes >= 1024 * 1024,
        "bytes ceiling should stay >= 1 MiB for debug smoke (got {bytes})"
    );
    assert!(allocs >= 1_000, "allocations ceiling should stay generous (got {allocs})");
}

#[test]
fn process_session_stays_under_allocation_budget() {
    let (bytes_ceiling, allocs_ceiling) = load_budget();
    let session = sample_session();

    // Warm once so one-time process/static init is outside the measured window.
    let _warm = session_ledger::process_session(&session);

    let region = Region::new(GLOBAL);
    let doc = session_ledger::process_session(&session);
    let delta = region.change();

    assert!(!doc.entities.is_empty() || !doc.source_id.is_empty(), "expected a non-empty OKF doc");

    eprintln!(
        "allocation-budget: bytes_allocated={} allocations={} (ceilings {} / {})",
        delta.bytes_allocated, delta.allocations, bytes_ceiling, allocs_ceiling
    );

    assert!(
        (delta.bytes_allocated as u64) <= bytes_ceiling,
        "bytes_allocated {} exceeds ceiling {}",
        delta.bytes_allocated,
        bytes_ceiling
    );
    assert!(
        (delta.allocations as u64) <= allocs_ceiling,
        "allocations {} exceeds ceiling {}",
        delta.allocations,
        allocs_ceiling
    );
}

#[test]
fn allocation_budget_script_self_check_parses_args_and_ceilings() {
    let script = repo_root().join("scripts/allocation-budget-check.ps1");
    assert!(script.is_file(), "missing {}", script.display());

    let output = Command::new("pwsh")
        .args(["-NoProfile", "-File", script.to_str().expect("utf-8 script path"), "-SelfCheck"])
        .output()
        .unwrap_or_else(|error| panic!("failed to spawn pwsh for self-check: {error}"));

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "allocation-budget-check.ps1 -SelfCheck failed\nstdout:\n{stdout}\nstderr:\n{stderr}"
    );
    assert!(
        stdout.contains("Self-check passed"),
        "expected self-check success line, got:\n{stdout}"
    );
    assert!(stdout.contains("Bytes ceiling:"), "expected bytes ceiling echo, got:\n{stdout}");
    assert!(
        stdout.contains("Allocations ceiling:"),
        "expected allocations ceiling echo, got:\n{stdout}"
    );
}
