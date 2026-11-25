//! Smoke test for the real corpus loader. Runs against the operator's
//! `$HOME/.codex/sessions`, `$HOME/.claude/projects`, `$HOME/.cursor/projects`
//! to confirm `DataSource::Auto` actually returns the sessions we expect.
//!
//! Skipped when no corpus roots are present (CI, sandbox, etc.) so it never
//! fails for the wrong reason.

use session_ledger::ports::CorpusSource;
use sl_viewer::corpus_loader::{load_sessions, DataSource};

/// Load just the cursor corpus. The cursor root on a typical install is the
/// smallest of the three (a handful of projects) so this exercises the
/// loader without paying the full multi-minute cost of the codex + claude
/// scan.
///
/// Both tests in this file are `#[ignore]`d by default. The full Auto scan
/// touches 13k+ files and takes minutes on real hardware, which would
/// block lefthook and any CI job that runs `cargo test` without a
/// dedicated corpus fixture. Run with:
///   cargo test -p sl-viewer --test corpus_smoke -- --ignored --nocapture
#[test]
#[ignore = "full local corpus scan blocks CI; run with --ignored"]
fn cursor_only_returns_real_sessions() {
    let home = match std::env::var_os("HOME") {
        Some(h) => std::path::PathBuf::from(h),
        None => return,
    };
    let cursor = home.join(".cursor").join("projects");
    if !cursor.is_dir() {
        eprintln!("skip: {} not a directory", cursor.display());
        return;
    }
    let started = std::time::Instant::now();
    let ids = session_ledger::CursorDir::new(cursor.clone()).list().expect("list cursor projects");
    eprintln!("cursor: {} projects in {:?}", ids.len(), started.elapsed());
    assert!(!ids.is_empty(), "cursor list is empty");
}

#[test]
#[ignore = "full local corpus scan blocks CI; run with --ignored"]
fn auto_source_returns_real_sessions_when_roots_exist() {
    let home = match std::env::var_os("HOME") {
        Some(h) => std::path::PathBuf::from(h),
        None => return, // nothing to test
    };
    let codex = home.join(".codex").join("sessions");
    let claude = home.join(".claude").join("projects");
    let cursor = home.join(".cursor").join("projects");

    if !codex.is_dir() && !claude.is_dir() && !cursor.is_dir() {
        eprintln!("skip: no codex/claude/cursor roots under {}", home.display());
        return;
    }

    let started = std::time::Instant::now();
    let sessions = load_sessions(&DataSource::Auto).expect("auto corpus load");
    eprintln!("auto: {} sessions in {:?}", sessions.len(), started.elapsed());
    assert!(!sessions.is_empty(), "DataSource::Auto returned 0 sessions from existing roots");
}
