//! Unit tests for the NDJSON helpers in the parent [`watch_capture`](super)
//! module.
//!
//! These live in a child module so the harness itself stays small enough to
//! read; behavior is unchanged.

use super::{assert_ndjson_frames, parse_ndjson_records, Capture};

fn capture(stdout: &str) -> Capture {
    Capture {
        stdout: stdout.to_string(),
        stderr: String::new(),
        reader_error: None,
        child_closed: false,
        detached_readers: Vec::new(),
        cleanup_error: None,
    }
}

fn panic_message(payload: Box<dyn std::any::Any + Send>) -> String {
    if let Some(text) = payload.downcast_ref::<String>() {
        return text.clone();
    }
    if let Some(text) = payload.downcast_ref::<&str>() {
        return (*text).to_string();
    }
    "<non-string panic>".to_string()
}

#[test]
fn newline_terminated_records_are_all_frames() {
    let records = parse_ndjson_records("{\"a\":1}\n{\"a\":2}\n");
    assert_eq!(records.frames, vec!["{\"a\":1}", "{\"a\":2}"]);
    assert!(records.truncated.is_none());
}

#[test]
fn fragment_without_newline_is_truncated_even_when_it_parses() {
    let records = parse_ndjson_records("{\"a\":1}\n{\"a\":2}");
    assert_eq!(records.frames, vec!["{\"a\":1}"]);
    assert_eq!(records.truncated.as_deref(), Some("{\"a\":2}"));
}

#[test]
fn malformed_fragment_without_newline_is_truncated() {
    let records = parse_ndjson_records("{\"a\":1}\n{\"a\":");
    assert_eq!(records.frames.len(), 1);
    assert_eq!(records.truncated.as_deref(), Some("{\"a\":"));
}

#[test]
fn truncated_tail_fails_the_frame_assertion() {
    let capture = capture("{\"a\":1}\n{\"a\":2}");
    let failure = std::panic::catch_unwind(|| assert_ndjson_frames(&capture, 1, "unit"))
        .expect_err("a newline-less trailing fragment MUST fail the assertion");
    let message = panic_message(failure);
    assert!(
        message.contains("truncated"),
        "panic message MUST name the truncation; got: {message}"
    );
}

#[test]
fn malformed_newline_terminated_record_fails_the_frame_assertion() {
    let capture = capture("{\"a\":1}\nnot json\n");
    assert!(
        std::panic::catch_unwind(|| assert_ndjson_frames(&capture, 1, "unit")).is_err(),
        "a malformed newline-terminated record MUST fail the assertion"
    );
}

#[test]
fn healthy_stream_returns_its_frames() {
    let capture = capture("{\"a\":1}\n{\"a\":2}\n");
    let frames = assert_ndjson_frames(&capture, 2, "unit");
    assert_eq!(frames, vec!["{\"a\":1}", "{\"a\":2}"]);
}
