//! FR-007 — `sharecli proc --pid N --watch` refresh surfaces
//! FR: FR-007
//!
//! AC-007.87 `proc --pid N --watch [secs]` text/NDJSON watch parity with flat `proc --watch`
//!
//! # Concurrency
//!
//! The three cases below run concurrently: none of them carries
//! `#[serial_test::serial]`. Each case owns a private `sharecli proc --pid N
//! --watch` child with its own stdout/stderr pipes, and the `proc` render
//! path is read-only — it reads `/proc`, `/sys` and (on macOS) `sysctl`, and
//! it never writes configuration, takes the serve lock, binds a socket or
//! starts a managed process. The watched PID is the test binary itself, which
//! is only ever inspected, never modified. Concurrent children therefore
//! cannot interfere with each other, and the per-test-binary wall clock is
//! one dwell window instead of three stacked ones.

use std::process::{Command, Stdio};
use std::time::Duration;

#[path = "support/watch_capture.rs"]
mod watch_capture;

use watch_capture::{assert_capture_healthy, assert_ndjson_frames, capture_watch};

fn bin() -> Command {
    Command::new(env!("CARGO_BIN_EXE_sharecli"))
}

const GATE_MARKER: &str = "=== Thermal Gate (FR-011) ===";
const WATCH_MARKER: &str = "=== Host Resource Watch ===";
const DETAIL_HEADER: &str = "=== Process detail (PID ";
const POOL_PREFIX: &str = "Pool node";
const PROC_PREFIX: &str = "Proc scan";
/// Watch-mode footer marker, emitted once per refresh frame.
const WATCH_FOOTER: &str = "[watch]";

/// Watch refresh interval handed to `sharecli` (seconds).
const WATCH_INTERVAL: &str = "1";

/// Refresh frames the assertions require.
const REQUIRED_FRAMES: usize = 2;

/// Wall-clock window the watcher child stays alive.
///
/// This preserves the original FR-007 semantics: the child runs for a full
/// 30 s window (many refresh cycles at a 1 s interval) and every assertion
/// runs against the complete captured output rather than a truncated prefix.
const DWELL: Duration = Duration::from_secs(30);

fn assert_gate_before_watch(segment: &str, context: &str) {
    let gate_pos = segment
        .find(GATE_MARKER)
        .unwrap_or_else(|| panic!("{context} MUST include gate section; got: {segment}"));
    let watch_pos = segment
        .find(WATCH_MARKER)
        .unwrap_or_else(|| panic!("{context} MUST include host watch section; got: {segment}"));
    assert!(
        gate_pos < watch_pos,
        "{context} MUST print gate before host watch; got: {segment}"
    );
}

fn assert_text_envelope_order(stdout: &str, context: &str) {
    let body_pos = stdout.find(DETAIL_HEADER).expect("proc detail header");
    let gate_pos = stdout.find(GATE_MARKER).expect("gate section");
    let watch_pos = stdout.find(WATCH_MARKER).expect("host watch section");
    let pool_pos = stdout.find(POOL_PREFIX).expect("pool operator line");
    let proc_pos = stdout.find(PROC_PREFIX).expect("proc-scan operator line");
    assert!(
        body_pos < gate_pos
            && gate_pos < watch_pos
            && watch_pos < pool_pos
            && pool_pos < proc_pos,
        "{context} MUST serialize detail → gate → host_watch → pool → proc-scan (AC-007.87); got: {stdout}"
    );
}

/// FR-007 / AC-007.87 — proc --pid --watch text keeps stderr silent across refresh cycles.
#[test]
fn fr007_proc_pid_watch_text_stderr_silent() {
    let pid = std::process::id();
    let mut child = bin()
        .args(["proc", "--pid", &pid.to_string(), "--watch", WATCH_INTERVAL])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn sharecli proc --pid --watch 1");

    let capture = capture_watch(&mut child, DWELL);
    assert_capture_healthy(&capture);

    assert!(
        capture.stderr.is_empty(),
        "proc --pid --watch text MUST keep stderr silent (AC-007.87); stderr: {:?}",
        capture.stderr
    );
    // Require multiple detail headers and footers independently. The final
    // refresh may be incomplete when the watcher is stopped.
    let frame_count = capture.stdout.matches(DETAIL_HEADER).count();
    let footer_count = capture.stdout.matches(WATCH_FOOTER).count();
    assert!(
        frame_count >= REQUIRED_FRAMES,
        "proc --pid --watch MUST re-render at least {REQUIRED_FRAMES} times; got {frame_count} \
         frames in: {}",
        capture.stdout
    );
    assert!(
        footer_count >= REQUIRED_FRAMES,
        "proc --pid --watch text MUST emit at least {REQUIRED_FRAMES} [watch] footers (AC-007.87); got \
         {footer_count} footers for {frame_count} frames in: {}",
        capture.stdout
    );
    assert_text_envelope_order(&capture.stdout, "proc --pid --watch");
    for (idx, segment) in capture.stdout.split(DETAIL_HEADER).skip(1).enumerate() {
        if segment.contains(WATCH_MARKER) {
            assert_gate_before_watch(segment, &format!("proc --pid --watch frame {}", idx + 1));
        }
    }
}

/// FR-007 / AC-007.87 — proc --pid --watch --json NDJSON stderr gate → host_watch companions.
#[test]
fn fr007_proc_pid_watch_ndjson_stderr_gate_before_host_watch() {
    let pid = std::process::id();
    let mut child = bin()
        .args([
            "proc",
            "--pid",
            &pid.to_string(),
            "--json",
            "--watch",
            WATCH_INTERVAL,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn sharecli proc --pid --json --watch 1");

    // NDJSON frames are stdout lines; the gate / host-watch companions and the
    // `[watch]` footer are emitted on stderr right after each frame.
    let capture = capture_watch(&mut child, DWELL);
    assert_capture_healthy(&capture);
    assert_ndjson_frames(&capture, REQUIRED_FRAMES, "proc --pid watch NDJSON");

    assert!(
        capture.stderr.contains(GATE_MARKER),
        "proc --pid watch NDJSON stderr MUST include gate companion (AC-007.87); stderr: {}",
        capture.stderr
    );
    assert!(
        capture.stderr.contains(WATCH_MARKER),
        "proc --pid watch NDJSON stderr MUST include host watch companion (AC-007.87); stderr: {}",
        capture.stderr
    );
    assert_gate_before_watch(&capture.stderr, "proc --pid watch NDJSON stderr");
    assert!(
        capture.stderr.contains(WATCH_FOOTER),
        "proc --pid watch NDJSON stderr MUST include [watch] footer; stderr: {}",
        capture.stderr
    );
}

/// FR-007 / AC-007.87 — proc --pid --watch --json stdout stays pipe-clean NDJSON.
#[test]
fn fr007_proc_pid_watch_ndjson_stdout_pipe_clean() {
    let pid = std::process::id();
    let mut child = bin()
        .args([
            "proc",
            "--pid",
            &pid.to_string(),
            "--json",
            "--watch",
            WATCH_INTERVAL,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn sharecli proc --pid --json --watch 1");

    // One NDJSON line per refresh frame on stdout.
    let capture = capture_watch(&mut child, DWELL);
    assert_capture_healthy(&capture);
    let frames = assert_ndjson_frames(&capture, REQUIRED_FRAMES, "proc --pid watch NDJSON stdout");

    assert!(
        !capture.stdout.contains(GATE_MARKER),
        "proc --pid watch NDJSON stdout MUST NOT leak gate companion (AC-007.87); got: {}",
        capture.stdout
    );
    assert!(
        !capture.stdout.contains(WATCH_MARKER),
        "proc --pid watch NDJSON stdout MUST NOT leak host watch companion (AC-007.87); got: {}",
        capture.stdout
    );
    assert!(
        !capture.stdout.contains(WATCH_FOOTER),
        "proc --pid watch NDJSON stdout MUST NOT contain watch footer (AC-007.87); got: {}",
        capture.stdout
    );
    assert!(
        !capture.stdout.contains("\x1b[2J"),
        "proc --pid watch NDJSON stdout MUST NOT contain terminal clear sequences"
    );

    for line in &frames {
        let v: serde_json::Value =
            serde_json::from_str(line.trim()).expect("each NDJSON stdout line MUST parse");
        assert!(v.get("ts").is_some(), "NDJSON line MUST include ts");
        assert!(
            v.get("pid").is_some(),
            "NDJSON line MUST include pid detail"
        );
        assert!(v.get("gate").is_some(), "NDJSON line MUST include gate");
        assert!(
            v.get("host_watch").is_some(),
            "NDJSON line MUST include host-watch"
        );
        assert!(
            v.get("pool").is_some(),
            "NDJSON line MUST include pool (AC-007.87)"
        );
        assert!(
            v.get("status").is_some(),
            "NDJSON line MUST include status (AC-007.87)"
        );
        let gate_pos = line.find("\"gate\"").expect("gate key in raw JSON");
        let host_pos = line
            .find("\"host_watch\"")
            .expect("host_watch key in raw JSON");
        assert!(
            gate_pos < host_pos,
            "NDJSON line MUST serialize gate before host-watch (AC-007.87); got: {line}"
        );
    }
}
