//! Test-only helpers shared by the module test suites.
//!
//! Kept behind `#[cfg(test)]` so it is never part of the shipped binary.

use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// Create a unique, empty directory under the OS temp dir.
///
/// Uniqueness comes from the process id plus a monotonic counter, so tests can
/// run in parallel without colliding. Callers remove the directory themselves
/// with [`remove`] once the assertions are done.
pub fn temp_dir(tag: &str) -> PathBuf {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    let dir = std::env::temp_dir().join(format!(
        "oci-lottery-test-{tag}-{}-{n}",
        std::process::id()
    ));
    std::fs::create_dir_all(&dir).expect("create temp dir");
    dir
}

/// Best-effort cleanup; a leftover temp dir must never fail a test.
pub fn remove(dir: &PathBuf) {
    let _ = std::fs::remove_dir_all(dir);
}
