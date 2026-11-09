//! Regression test for integer encoding across MCP clients.
//!
//! The published input schema says `"type": "integer"`, but real clients are
//! not consistent: the agent harness these tools are registered with sends
//! the value quoted, e.g. `"ttl_ms": "30000"`. Serde's default is strict, so
//! the tool answered `invalid type: string "30000", expected u64` and the call
//! failed before it reached the broker.
//!
//! Both encodings must be accepted. What must still be rejected: a value that
//! is neither, a string that does not parse, and a negative or fractional
//! number - a fencing token has to be an exact number, not something the broker
//! rounds, clamps or guesses.

use substrate_browser_mcp::{AcquireParams, ReleaseParams};

#[test]
fn ttl_ms_accepts_a_json_number() {
    let params: AcquireParams =
        serde_json::from_str(r#"{"principal":"alice","profile":"work","ttl_ms":30000}"#)
            .expect("a JSON number must be accepted");
    assert_eq!(params.ttl_ms, Some(30_000));
}

#[test]
fn ttl_ms_accepts_a_numeric_string() {
    let params: AcquireParams =
        serde_json::from_str(r#"{"principal":"alice","profile":"work","ttl_ms":"30000"}"#)
            .expect("a numeric string must be accepted");
    assert_eq!(params.ttl_ms, Some(30_000));
}

#[test]
fn fencing_token_accepts_both_encodings() {
    let from_number: ReleaseParams =
        serde_json::from_str(r#"{"lease_id":"lease-1","fencing_token":7}"#).expect("number");
    let from_string: ReleaseParams =
        serde_json::from_str(r#"{"lease_id":"lease-1","fencing_token":"7"}"#)
            .expect("numeric string");
    assert_eq!(from_number.fencing_token, 7);
    assert_eq!(from_string.fencing_token, 7);
}

#[test]
fn a_non_numeric_string_is_still_rejected() {
    let err = serde_json::from_str::<AcquireParams>(
        r#"{"principal":"alice","profile":"work","ttl_ms":"not-a-number"}"#,
    )
    .expect_err("a non-numeric string must be rejected");
    assert!(err.to_string().contains("not-a-number"), "got: {err}");
}

#[test]
fn a_negative_value_is_still_rejected() {
    // u64 cannot be negative; a client sending -1 must get an error rather
    // than a silently clamped value.
    serde_json::from_str::<AcquireParams>(
        r#"{"principal":"alice","profile":"work","ttl_ms":-1}"#,
    )
    .expect_err("a negative ttl must be rejected");
}

#[test]
fn a_float_is_still_rejected() {
    // 30000.5 is not an integer; truncating it would change the lease TTL.
    serde_json::from_str::<AcquireParams>(
        r#"{"principal":"alice","profile":"work","ttl_ms":30000.5}"#,
    )
    .expect_err("a fractional ttl must be rejected");
}
