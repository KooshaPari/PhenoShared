//! Shared watch-capture harness for the FR-007 `sharecli ... --watch` tests.
//!
//! The harness exists because every FR-007 watch case has the same problem:
//! `sharecli` in watch mode never exits on its own, so the test has to start
//! the child, collect its output for a fixed dwell window, stop it, and then
//! make sure that neither the child nor a reader thread outlives the test.
//!
//! # Bounded teardown
//!
//! [`capture_watch`] runs in five stages: spawn the pipe readers, collect for
//! the dwell window, settle until the pipes have been quiet for
//! [`QUIET_PERIOD`] (or [`KILL_GRACE`] elapses), kill and reap the child,
//! drain the bytes the readers already buffered, then join the readers.
//!
//! Every wait in the teardown path is bounded: the reap, the post-kill drain,
//! and the reader-thread joins.
//!
//! A process that inherited the pipe write end keeps the pipes open, so a
//! reader thread can stay blocked in `read()` forever. Such a reader is
//! detached rather than joined, and the capture reports it as a failure
//! instead of hanging.

use std::io::Read;
use std::process::Child;
use std::sync::mpsc::{self, RecvTimeoutError, SyncSender};
use std::thread;
use std::time::{Duration, Instant};

/// Poll granularity while collecting pipe output.
pub const POLL_INTERVAL: Duration = Duration::from_millis(25);

/// The pipe-quiet duration that ends data collection before the stop signal.
///
/// The capture keeps reading until no new bytes have arrived for this long
/// (bounded by [`KILL_GRACE`]). This reduces, but does not eliminate, the
/// chance of stopping the watcher mid-write: a write can begin immediately
/// after the quiet check. A trailing fragment without its newline terminator
/// is therefore treated as truncated output, never as a complete record.
const QUIET_PERIOD: Duration = Duration::from_millis(200);

/// Upper bound on the wait for that idle window.
const KILL_GRACE: Duration = Duration::from_secs(2);

/// Upper bound on the post-kill drain of already-buffered pipe data.
const DRAIN_DEADLINE: Duration = Duration::from_secs(3);

/// Upper bound on reaping the child after the stop signal. A child that is
/// not reaped within this window is reported as a teardown failure rather
/// than waited on without limit.
const REAP_DEADLINE: Duration = Duration::from_secs(5);

/// Upper bound on waiting for a reader thread to observe EOF.
const JOIN_DEADLINE: Duration = Duration::from_secs(3);

/// Bounded channel capacity, in pipe chunks, between the reader threads and
/// the capture loop. Bounding it keeps a chatty child from growing the
/// channel without limit.
const CHANNEL_CAPACITY: usize = 256;

/// Size of a single pipe read.
const READ_CHUNK: usize = 8192;

/// Which pipe an event came from.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Stream {
    Stdout,
    Stderr,
}

impl Stream {
    fn as_str(self) -> &'static str {
        match self {
            Stream::Stdout => "stdout",
            Stream::Stderr => "stderr",
        }
    }
}

/// A single event produced by a pipe reader thread.
enum PipeEvent {
    /// Raw bytes read from a pipe.
    Data { stream: Stream, bytes: Vec<u8> },
    /// The pipe could not be read any further.
    ReaderError { stream: Stream, error: String },
}

/// Read `pipe` to EOF, forwarding every chunk to `tx`.
///
/// A read error is reported as a [`PipeEvent::ReaderError`] so the capture
/// loop can fail loudly instead of silently truncating the output.
fn spawn_reader<R: Read + Send + 'static>(
    mut pipe: R,
    stream: Stream,
    tx: SyncSender<PipeEvent>,
) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        let mut buf = [0u8; READ_CHUNK];
        loop {
            match pipe.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    let event = PipeEvent::Data {
                        stream,
                        bytes: buf[..n].to_vec(),
                    };
                    if tx.send(event).is_err() {
                        break;
                    }
                },
                Err(e) => {
                    let _ = tx.send(PipeEvent::ReaderError {
                        stream,
                        error: e.to_string(),
                    });
                    break;
                },
            }
        }
    })
}

/// Everything a capture observed.
pub struct Capture {
    /// stdout bytes seen during the dwell.
    pub stdout: String,
    /// stderr bytes seen during the dwell.
    pub stderr: String,
    /// Set when a reader thread reported a read error.
    reader_error: Option<String>,
    /// Set when the child closed both pipes before the dwell elapsed.
    child_closed: bool,
    /// Streams whose reader thread did not finish within the join bound and
    /// was therefore detached. A detached reader is still blocked in
    /// `read()` on the pipe it inherited; the capture cannot join it and says
    /// so instead of pretending the teardown was clean.
    detached_readers: Vec<&'static str>,
    /// Set when stopping or reaping the child failed, including a child that
    /// did not exit within [`REAP_DEADLINE`].
    cleanup_error: Option<String>,
}

/// Capture the watcher child's output for the full `dwell` window.
///
/// The child is stopped and reaped. Every wait in the teardown path is
/// bounded: the reap, the post-kill drain, and the reader-thread joins. A
/// child that cannot be stopped or reaped is reported as a capture failure
/// instead of being waited on forever. A process that
/// inherited the pipe write end keeps the pipes open, so a reader can block
/// in `read()` forever — such a reader is detached instead of joined, so the
/// capture can never turn into an unbounded wait.
pub fn capture_watch(child: &mut Child, dwell: Duration) -> Capture {
    let stdout_pipe = child.stdout.take().expect("piped stdout");
    let stderr_pipe = child.stderr.take().expect("piped stderr");

    // Bounded channel: the reader threads can never run more than
    // CHANNEL_CAPACITY chunks ahead of the capture loop.
    let (tx, rx) = mpsc::sync_channel::<PipeEvent>(CHANNEL_CAPACITY);
    let stdout_thread = spawn_reader(stdout_pipe, Stream::Stdout, tx.clone());
    let stderr_thread = spawn_reader(stderr_pipe, Stream::Stderr, tx);

    let mut stdout_bytes: Vec<u8> = Vec::new();
    let mut stderr_bytes: Vec<u8> = Vec::new();
    let mut reader_error: Option<String> = None;
    let mut child_closed = false;

    let start = Instant::now();
    let mut last_data_at = start;

    // Dwell: keep the child alive for the whole window so that many refresh
    // cycles are exercised, exactly like the original 30 s dwell.
    while start.elapsed() < dwell {
        match rx.recv_timeout(POLL_INTERVAL) {
            Ok(PipeEvent::Data { stream, bytes }) => {
                last_data_at = Instant::now();
                match stream {
                    Stream::Stdout => stdout_bytes.extend_from_slice(&bytes),
                    Stream::Stderr => stderr_bytes.extend_from_slice(&bytes),
                }
            },
            Ok(PipeEvent::ReaderError { stream, error }) => {
                reader_error = Some(format!("{} reader failed: {error}", stream.as_str()));
            },
            Err(RecvTimeoutError::Timeout) => {},
            // Both readers dropped their senders, i.e. both pipes hit EOF,
            // i.e. the child closed its output and is on its way out.
            Err(RecvTimeoutError::Disconnected) => {
                child_closed = true;
                break;
            },
        }
        if reader_error.is_some() {
            break;
        }
    }

    // Settle before stopping: keep reading until the pipes have been quiet
    // for QUIET_PERIOD so the child has normally finished its current frame.
    // This is a heuristic, not a guarantee — a write can start right after
    // the quiet check — so a partial trailing record is possible and is
    // reported as truncated rather than silently accepted.
    let quiet_deadline = Instant::now() + KILL_GRACE;
    while Instant::now() < quiet_deadline && last_data_at.elapsed() < QUIET_PERIOD {
        match rx.recv_timeout(POLL_INTERVAL) {
            Ok(PipeEvent::Data { stream, bytes }) => {
                last_data_at = Instant::now();
                match stream {
                    Stream::Stdout => stdout_bytes.extend_from_slice(&bytes),
                    Stream::Stderr => stderr_bytes.extend_from_slice(&bytes),
                }
            },
            Ok(PipeEvent::ReaderError { stream, error }) => {
                reader_error = Some(format!("{} reader failed: {error}", stream.as_str()));
            },
            Err(RecvTimeoutError::Timeout) => {},
            Err(RecvTimeoutError::Disconnected) => {
                child_closed = true;
                break;
            },
        }
    }

    // Stop the watch process with a bounded reap, then take whatever the
    // readers already buffered so that no already-written frame is lost.
    let cleanup_error = stop_and_reap(child);

    // Bounded drain: a process that inherited the pipe write end keeps the
    // pipes open, so the readers may never observe EOF.
    let drain_deadline = Instant::now() + DRAIN_DEADLINE;
    loop {
        let remaining = drain_deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            break;
        }
        match rx.recv_timeout(remaining.min(POLL_INTERVAL)) {
            Ok(PipeEvent::Data { stream, bytes }) => match stream {
                Stream::Stdout => stdout_bytes.extend_from_slice(&bytes),
                Stream::Stderr => stderr_bytes.extend_from_slice(&bytes),
            },
            Ok(PipeEvent::ReaderError { stream, error }) => {
                reader_error = Some(format!("{} reader failed: {error}", stream.as_str()));
            },
            Err(RecvTimeoutError::Timeout) => {},
            Err(RecvTimeoutError::Disconnected) => break,
        }
    }

    // Releasing the receiver makes the readers stop as soon as their next
    // `send` fails.
    drop(rx);

    // Bounded join: a reader can stay blocked in `read()` forever when
    // another process inherited the pipe write end, so a reader that does not
    // finish in time is detached rather than joined.
    let mut detached_readers: Vec<&'static str> = Vec::new();
    match join_bounded(stdout_thread, JOIN_DEADLINE) {
        Ok(true) => {},
        Ok(false) => detached_readers.push("stdout"),
        Err(panic_message) => reader_error = Some(format!("stdout {panic_message}")),
    }
    match join_bounded(stderr_thread, JOIN_DEADLINE) {
        Ok(true) => {},
        Ok(false) => detached_readers.push("stderr"),
        Err(panic_message) => reader_error = Some(format!("stderr {panic_message}")),
    }

    Capture {
        stdout: String::from_utf8_lossy(&stdout_bytes).into_owned(),
        stderr: String::from_utf8_lossy(&stderr_bytes).into_owned(),
        reader_error,
        child_closed,
        detached_readers,
        cleanup_error,
    }
}

/// Stop and reap `child` within [`REAP_DEADLINE`], reporting every failure.
///
/// Returns `None` when the child is confirmed reaped (or was already reaped
/// before the call). Any other outcome — a kill that failed while the child
/// was still running, a `try_wait` error, or a child still running at the
/// deadline — is returned as a description so the test fails loudly instead
/// of leaking a live watcher.
fn stop_and_reap(child: &mut Child) -> Option<String> {
    // Never wait without a bound: poll the child instead of blocking in
    // `wait()`. A watcher that ignores the stop signal would otherwise hang
    // the test binary.
    match child.try_wait() {
        Ok(Some(_)) => return None,
        Ok(None) => {},
        Err(e) => return Some(format!("try_wait failed: {e}")),
    }
    let mut problems: Vec<String> = Vec::new();
    match child.kill() {
        Ok(()) => {},
        Err(e) => {
            // `kill` can fail because the child exited between the `try_wait`
            // above and this call. That race is benign, and its errno is not
            // portable (`ESRCH` is 3 on Linux and macOS but is not guaranteed
            // to be 3 on every platform), so confirm the child's state with
            // `try_wait` instead of matching a raw errno integer.
            match child.try_wait() {
                // The child is gone: the kill failure was only the race.
                Ok(Some(_)) => return None,
                Ok(None) => {
                    problems.push(format!(
                        "kill failed while the child was still running: {e}"
                    ));
                },
                Err(wait_err) => {
                    problems.push(format!(
                        "kill failed: {e}; try_wait after the failed kill also failed: {wait_err}"
                    ));
                    return Some(problems.join("; "));
                },
            }
        },
    }
    let deadline = Instant::now() + REAP_DEADLINE;
    loop {
        match child.try_wait() {
            Ok(Some(_)) => break,
            Ok(None) => {},
            Err(e) => {
                problems.push(format!("try_wait failed: {e}"));
                return Some(problems.join("; "));
            },
        }
        if Instant::now() >= deadline {
            problems.push(format!(
                "child still running {REAP_DEADLINE:?} after the stop signal"
            ));
            return Some(problems.join("; "));
        }
        thread::sleep(POLL_INTERVAL);
    }
    if problems.is_empty() {
        None
    } else {
        // The reap succeeded, but the stop signal itself was defective;
        // report it rather than discard it.
        Some(problems.join("; "))
    }
}

/// Join `handle` if it finishes within `bound`; detach it otherwise.
///
/// `Ok(true)` means the thread was joined, `Ok(false)` means it outlived the
/// bound and was detached, `Err` means the thread panicked.
fn join_bounded(handle: thread::JoinHandle<()>, bound: Duration) -> Result<bool, String> {
    let deadline = Instant::now() + bound;
    while Instant::now() < deadline {
        if handle.is_finished() {
            return handle
                .join()
                .map(|()| true)
                .map_err(|_| "reader thread panicked".to_string());
        }
        thread::sleep(POLL_INTERVAL);
    }
    Ok(false)
}

/// Panic with the captured output when the capture itself failed.
pub fn assert_capture_healthy(capture: &Capture) {
    if let Some(error) = &capture.reader_error {
        panic!(
            "sharecli watch {error}\nstdout:\n{}\nstderr:\n{}",
            capture.stdout, capture.stderr
        );
    }
    if !capture.detached_readers.is_empty() {
        panic!(
            "sharecli watch {} reader thread(s) did not finish within {JOIN_DEADLINE:?} and were \
             detached; they may still be blocked in read() because another process holds the pipe \
             write end open\nstdout:\n{}\nstderr:\n{}",
            capture.detached_readers.join(", "),
            capture.stdout,
            capture.stderr
        );
    }
    if let Some(error) = &capture.cleanup_error {
        panic!(
            "sharecli watch process teardown failed: {error}\nstdout:\n{}\nstderr:\n{}",
            capture.stdout, capture.stderr
        );
    }
    if capture.child_closed {
        panic!(
            "sharecli watch child exited before the dwell window elapsed\nstdout:\n{}\nstderr:\n{}",
            capture.stdout, capture.stderr
        );
    }
}

/// NDJSON records extracted from captured stdout.
pub struct NdjsonRecords {
    /// Complete records, in emission order.
    pub frames: Vec<String>,
    /// A trailing fragment left behind by the capture kill, when the fragment
    /// was not a complete record.
    pub truncated: Option<String>,
}

/// Extract NDJSON records from captured stdout.
///
/// Every byte is accounted for: newline-terminated records become frames, and
/// any trailing fragment is reported as truncated. The newline is the record
/// terminator, so a fragment without one is incomplete output even when the
/// bytes happen to parse as JSON — it is never promoted to a frame.
pub fn parse_ndjson_records(text: &str) -> NdjsonRecords {
    let mut frames: Vec<String> = Vec::new();
    let mut start = 0usize;
    for (idx, ch) in text.char_indices() {
        if ch != '\n' {
            continue;
        }
        let line = text[start..idx].trim();
        if !line.is_empty() {
            frames.push(line.to_string());
        }
        start = idx + ch.len_utf8();
    }
    let tail = text[start..].trim();
    // The newline is the record terminator. Whatever remains past the last
    // one lacks that terminator, so it is truncated output: asserting on it
    // (rather than ignoring or promoting it) keeps the strict original
    // behavior.
    let truncated = if tail.is_empty() {
        None
    } else {
        Some(tail.to_string())
    };
    NdjsonRecords { frames, truncated }
}

/// Assert the capture produced at least `required` valid NDJSON records and
/// return them.
///
/// The returned records are the exact set the stop condition counts, so the
/// stop condition and the assertions can never disagree about what the
/// product emitted.
pub fn assert_ndjson_frames(capture: &Capture, required: usize, context: &str) -> Vec<String> {
    let records = parse_ndjson_records(&capture.stdout);
    assert!(
        records.frames.len() >= required,
        "{context} MUST emit at least {required} NDJSON frames; got {} in: {}",
        records.frames.len(),
        capture.stdout
    );
    for frame in &records.frames {
        serde_json::from_str::<serde_json::Value>(frame)
            .unwrap_or_else(|e| panic!("{context} NDJSON frame MUST parse; got {frame}: {e}"));
    }
    if let Some(fragment) = &records.truncated {
        // A fragment without a terminating newline is incomplete output. It
        // must fail the assertion: silently dropping it would let a real
        // truncation (a short write, or a capture that stopped mid-record)
        // pass as a healthy stream.
        panic!(
            "{context} NDJSON stream MUST be newline-terminated per record; the trailing \
             {}-byte fragment has no terminator and is truncated; fragment: {fragment:?}\n\
             stdout:\n{}",
            fragment.len(),
            capture.stdout
        );
    }
    records.frames
}

#[cfg(test)]
#[path = "watch_capture/ndjson_tests.rs"]
mod ndjson_tests;
