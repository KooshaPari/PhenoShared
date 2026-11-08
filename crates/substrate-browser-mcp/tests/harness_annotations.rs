//! Regression test for the harness-annotation incompatibility.
//!
//! MCP clients - including the agent harness these tools are registered with -
//! attach `intent` to **every** tool call. The parameter structs are
//! `deny_unknown_fields`, so without an explicit slot for those annotations
//! every `broker_acquire`, `broker_release` and `broker_purge` call was
//! rejected with "unknown field `intent`" before it ever reached the broker.
//!
//! The fix must accept the annotations **without** weakening the typo
//! protection: a misspelled broker field must still be an error, because
//! silently defaulting it would mean acting on the wrong profile.

use substrate_browser_mcp::{AcquireParams, PurgeParams, ReleaseParams};

#[test]
fn acquire_accepts_harness_intent() {
    let params: AcquireParams = serde_json::from_str(
        r#"{"principal":"alice","profile":"work","intent":"why the call is made"}"#,
    )
    .expect("intent must be accepted");
    assert_eq!(params.principal, "alice");
    assert_eq!(params.profile, "work");
    assert_eq!(
        params.annotations.intent.as_deref(),
        Some("why the call is made")
    );
}

#[test]
fn acquire_accepts_harness_accept_large_output() {
    let params: AcquireParams = serde_json::from_str(
        r#"{"principal":"alice","profile":"work","accept_large_output":true}"#,
    )
    .expect("accept_large_output must be accepted");
    assert_eq!(params.annotations.accept_large_output, Some(true));
}

#[test]
fn release_accepts_harness_intent() {
    let params: ReleaseParams =
        serde_json::from_str(r#"{"lease_id":"lease-1","fencing_token":7,"intent":"release it"}"#)
            .expect("intent must be accepted");
    assert_eq!(params.lease_id, "lease-1");
    assert_eq!(params.fencing_token, 7);
}

#[test]
fn purge_accepts_harness_intent() {
    let params: PurgeParams = serde_json::from_str(
        r#"{"principal":"alice","profile":"work","confirm":true,"intent":"purge"}"#,
    )
    .expect("intent must be accepted");
    assert!(params.confirm);
}

#[test]
fn a_typo_in_a_broker_field_is_still_rejected() {
    // The whole point of keeping `deny_unknown_fields`: a misspelled field
    // must not silently fall back to a default.
    let err = serde_json::from_str::<AcquireParams>(
        r#"{"principal":"alice","profile":"work","scope":"s1"}"#,
    )
    .expect_err("a typo must still be rejected");
    let msg = err.to_string();
    assert!(
        msg.contains("scope"),
        "the error should name the offending field, got: {msg}"
    );
}

#[test]
fn an_unknown_field_besides_the_annotations_is_still_rejected() {
    let err = serde_json::from_str::<AcquireParams>(
        r#"{"principal":"alice","profile":"work","intent":"x","scpoe":"typo"}"#,
    )
    .expect_err("an unrelated unknown field must still be rejected");
    assert!(err.to_string().contains("scpoe"), "got: {err}");
}
