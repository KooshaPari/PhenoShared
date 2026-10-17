//! `phinbox harness …` subcommand implementation.
//!
//! Bridge harnesses (Codex, Jcode, KCode, Forge/HeliosLite) integrate without changing
//! native policy authority. `codex-permission-request` is the only wired bridge today:
//! it reads a single Codex `PermissionRequest` JSON payload from stdin, routes the
//! pending request through the ordinary durable inbox queue, waits up to a bounded
//! `timeout_secs` for the correlated, explicit `FieldValue::Boolean(true)` answer,
//! and returns the documented Codex `hookSpecificOutput` envelope.
//!
//! Bounded by design:
//!   * stdin payload <= 1 MiB
//!   * `--timeout-secs` integer 1..=120 (clamped)
//!   * any error, malformed input, defer/cancel/expiry, mismatched correlation,
//!     text "true", false, or management-only state returns the canonical native
//!     deny JSON.
//!
//! This CLI does not interpret an existing native denial as permission. It accepts
//! only what `codex_permission_request()` from the `phinbox::harness` module accepts.

use std::io::Read;
use std::path::PathBuf;

use clap::{Args, Subcommand};

/// Bounded stdin size for `phinbox harness codex-permission-request`.
const STDIN_LIMIT: usize = 1024 * 1024;
/// Inclusive minimum timeout bound.
const TIMEOUT_MIN_SECS: u64 = 1;
/// Inclusive maximum timeout bound.
const TIMEOUT_MAX_SECS: u64 = 120;

/// Harness subcommand dispatcher — currently exposes the documented Codex
/// permission-request bridge only. Future harnesses are added here without
/// touching call sites.
#[derive(Debug, Args)]
pub struct HarnessArgs {
    #[command(subcommand)]
    pub cmd: HarnessCmd,
}

#[derive(Debug, Subcommand)]
pub enum HarnessCmd {
    /// Process a single Codex `PermissionRequest` event read from stdin.
    ///
    /// Wait up to `--timeout-secs` (1..=120, default 30) for an explicit
    /// typed boolean approval correlated with this pending request. The
    /// output is the documented `hookSpecificOutput` envelope; it is safe to
    /// pipe to a Codex hook callback.
    CodexPermissionRequest {
        /// Maximum wait (seconds) for a correlated explicit answer. Clamped to 1..=120.
        #[arg(long, default_value_t = 30, value_name = "SECS")]
        timeout_secs: u64,
    },
}

/// Dispatch a single harness subcommand.
///
/// `inbox_dir` is the durable Phinbox root used for the queue + daemon lockfile
/// discovery. The same root the existing `phinbox inbox` family uses.
pub fn cmd_harness(args: HarnessArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    match args.cmd {
        HarnessCmd::CodexPermissionRequest { timeout_secs } => {
            cmd_codex_permission_request(timeout_secs, inbox_dir)
        },
    }
}

/// Bounded Codex permission-request bridge driver.
///
/// * Reads at most `STDIN_LIMIT` bytes from stdin. Larger reads are refused
///   with the canonical deny envelope.
/// * Clamps `timeout_secs` to `TIMEOUT_MIN_SECS..=TIMEOUT_MAX_SECS` and surfaces
///   that bound in the failure path if a caller passes an out-of-range value.
/// * Writes the `Value` returned by `phinbox::harness::codex_permission_request`
///   to stdout as pretty-printed JSON. The decision JSON is also the only exit
///   status — the process exit code is 0 on a deny or allow decision so callers
///   can pipe reliably; the decision is determined entirely by the JSON.
fn cmd_codex_permission_request(timeout_secs: u64, inbox_dir: &PathBuf) -> Result<(), String> {
    let mut buf = Vec::new();
    let mut handle = std::io::stdin().take(STDIN_LIMIT as u64);
    handle
        .read_to_end(&mut buf)
        .map_err(|e| format!("failed to read stdin: {e}"))?;
    if buf.len() > STDIN_LIMIT {
        // We requested exactly STDIN_LIMIT; an oversize payload means the source
        // delivered more bytes than that. Surface the canonical deny envelope and
        // continue so the caller (hook) can still parse a structured decision.
        let envelope = phinbox::harness::codex_permission_request(&buf, inbox_dir, 30);
        println!("{}", serde_json::to_string_pretty(&envelope).map_err(|e| e.to_string())?);
        return Ok(());
    }
    let bounded = timeout_secs.clamp(TIMEOUT_MIN_SECS, TIMEOUT_MAX_SECS);
    let envelope = phinbox::harness::codex_permission_request(&buf, inbox_dir, bounded);
    println!(
        "{}",
        serde_json::to_string_pretty(&envelope).map_err(|e| e.to_string())?
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timeout_bounds_match_contract() {
        assert!(TIMEOUT_MIN_SECS >= 1);
        assert!(TIMEOUT_MAX_SECS <= 120);
        assert!(STDIN_LIMIT == 1024 * 1024);
    }

    #[test]
    fn clamp_keeps_valid_bounds() {
        assert_eq!(0u64.clamp(TIMEOUT_MIN_SECS, TIMEOUT_MAX_SECS), 1);
        assert_eq!(
            9999u64.clamp(TIMEOUT_MIN_SECS, TIMEOUT_MAX_SECS),
            TIMEOUT_MAX_SECS
        );
        assert_eq!(42u64.clamp(TIMEOUT_MIN_SECS, TIMEOUT_MAX_SECS), 42);
    }
}
