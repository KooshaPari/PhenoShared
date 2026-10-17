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
//!   * stdin payload <= 1 MiB (read bounded to `STDIN_LIMIT + 1` so oversize is
//!     detectable and rejected, never silently truncated)
//!   * `--timeout-secs` integer 1..=120 — invalid values are rejected via the
//!     canonical native deny envelope, never silently clamped
//!   * any error, malformed input, defer/cancel/expiry, mismatched correlation,
//!     text "true", false, or management-only state returns the canonical native
//!     deny JSON
//!   * stdin read I/O failures are converted into the deny envelope rather than
//!     propagated as `Err`/non-zero exit code, so hooks that pipe the decision
//!     JSON cannot fail-open on infrastructure errors
//!
//! This CLI does not interpret an existing native denial as permission. It accepts
//! only what `codex_permission_request()` from the `phinbox::harness` module accepts.

use std::io::{self, Read};
use std::path::PathBuf;

use clap::{Args, Subcommand};
use serde_json::{json, Value};

/// Bounded stdin size for `phinbox harness codex-permission-request`.
const STDIN_LIMIT: usize = 1024 * 1024;

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
        /// Maximum wait (seconds) for a correlated explicit answer. Must
        /// be an integer in `1..=120`; out-of-range values deny immediately.
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

/// Outcome of reading a bounded prefix of a stream.
#[derive(Debug)]
enum ReadOutcome {
    /// Read succeeded and stayed within the limit.
    Bounded(Vec<u8>),
    /// Read succeeded but the source delivered more than `limit` bytes. The
    /// vec contains exactly `limit + 1` bytes (the oversize probe) so the
    /// caller can detect the violation without dropping data.
    Oversize(Vec<u8>),
    /// Read returned an I/O error before any usable payload was assembled.
    IoError(String),
}

/// Read up to `limit` bytes from `reader`, but read `limit + 1` so an oversize
/// source is detectable. The caller picks the action.
fn read_bounded<R: Read>(reader: &mut R, limit: usize) -> ReadOutcome {
    let mut buf = Vec::new();
    let mut take = reader.take((limit as u64) + 1);
    match take.read_to_end(&mut buf) {
        Ok(_) => {
            if buf.len() > limit {
                ReadOutcome::Oversize(buf)
            } else {
                ReadOutcome::Bounded(buf)
            }
        },
        Err(e) => ReadOutcome::IoError(e.to_string()),
    }
}

/// Render the canonical Codex bridge deny envelope as pretty JSON. Used both
/// for I/O-error path (where we have no input to forward to the bridge) and as
/// a sanity check inside the test suite.
fn deny_envelope(reason: &str) -> Value {
    json!({
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": "deny",
                "message": reason,
            }
        }
    })
}

/// Bounded Codex permission-request bridge driver.
///
/// * Reads stdin into a buffer bounded to `STDIN_LIMIT` bytes by consuming
///   `STDIN_LIMIT + 1` so oversize input is observable. Any input past the
///   limit produces the canonical deny envelope via the bridge (which owns
///   the `input.len() > LIMIT` guard) — never a silent truncation followed by
///   a normal answer.
/// * Any stdin read I/O error converts into the deny envelope rather than
///   propagating the error as a non-zero exit that hooks might fail-open on.
/// * Invalid `timeout_secs` (outside `1..=120`) forwards the value verbatim to
///   the bridge so its own `(1..=120).contains(&timeout_secs)` guard returns
///   the deny envelope — invalid values never reach `wait_for_response`.
/// * The `Value` returned by `phinbox::harness::codex_permission_request` is
///   printed as pretty JSON. The exit code is 0 on a deny or allow decision
///   so callers can pipe reliably; the decision is determined entirely by the
///   JSON contents.
fn cmd_codex_permission_request(timeout_secs: u64, inbox_dir: &PathBuf) -> Result<(), String> {
    let stdin = io::stdin();
    let mut handle = stdin.lock();
    let outcome = read_bounded(&mut handle, STDIN_LIMIT);
    let envelope = match outcome {
        ReadOutcome::IoError(msg) => deny_envelope(&format!(
            "Phinbox could not read Codex permission request from stdin: {msg}"
        )),
        ReadOutcome::Oversize(buf) | ReadOutcome::Bounded(buf) => {
            // Forward the byte-for-byte contents to the bridge. The bridge
            // owns the `input.len() > LIMIT` and `!(1..=120).contains(&secs)`
            // guards. Invalid timeouts are NEVER silently rewritten.
            phinbox::harness::codex_permission_request(&buf, inbox_dir, timeout_secs)
        },
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&envelope).map_err(|e| e.to_string())?
    );
    Ok(())
}

// Public-from-integration-test surface (no-op in production). Exposed so the
// process-level CLI tests below can exercise the bounded-stdin cap.
#[doc(hidden)]
pub const STDIN_LIMIT_BYTES: usize = STDIN_LIMIT;

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Cursor, Read};

    /// Always-errors reader, used to exercise the I/O-error code path without
    /// needing to break the real stdin file descriptor.
    struct FailingReader;
    impl Read for FailingReader {
        fn read(&mut self, _buf: &mut [u8]) -> io::Result<usize> {
            Err(io::Error::new(io::ErrorKind::Other, "synthetic read failure"))
        }
    }

    #[test]
    fn read_bounded_returns_oversize_when_limit_exceeded() {
        // 1 MiB of valid UTF-8 padding plus one extra byte triggers oversize.
        let oversized = vec![b'x'; STDIN_LIMIT + 1];
        let mut cursor = Cursor::new(oversized);
        match read_bounded(&mut cursor, STDIN_LIMIT) {
            ReadOutcome::Oversize(buf) => assert_eq!(buf.len(), STDIN_LIMIT + 1),
            other => panic!("expected Oversize, got {:?}", other),
        }
    }

    #[test]
    fn read_bounded_returns_bounded_when_at_limit() {
        let exact = vec![b'y'; STDIN_LIMIT];
        let mut cursor = Cursor::new(exact);
        match read_bounded(&mut cursor, STDIN_LIMIT) {
            ReadOutcome::Bounded(buf) => assert_eq!(buf.len(), STDIN_LIMIT),
            other => panic!("expected Bounded, got {:?}", other),
        }
    }

    #[test]
    fn read_bounded_returns_io_error_when_reader_fails() {
        let mut reader = FailingReader;
        match read_bounded(&mut reader, STDIN_LIMIT) {
            ReadOutcome::IoError(msg) => assert!(msg.contains("synthetic read failure")),
            other => panic!("expected IoError, got {:?}", other),
        }
    }

    #[test]
    fn deny_envelope_decision_is_deny_with_reason() {
        let v = deny_envelope("test reason");
        assert_eq!(
            v["hookSpecificOutput"]["hookEventName"],
            serde_json::json!("PermissionRequest")
        );
        assert_eq!(
            v["hookSpecificOutput"]["decision"]["behavior"],
            serde_json::json!("deny")
        );
        assert_eq!(
            v["hookSpecificOutput"]["decision"]["message"],
            serde_json::json!("test reason")
        );
    }
}
