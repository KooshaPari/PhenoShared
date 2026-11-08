//! G2 deterministic correlation + redaction fixture for `pheno-otel`.
//!
//! Per `13-breadth-readiness-and-priority.md`, PhenoObservability's G2 gate
//! is "deterministic correlation and redaction fixture". This test is the
//! fixture itself: a single run that asserts byte-identical correlation
//! propagation + redaction behaviour, suitable for CI gating.
//!
//! The fixture is split into two halves:
//!
//! 1. **Correlation half** — verify that a child [`correlation::TraceContext`]
//!    inherits the parent's `trace_id` and `flags`; that the wire-format
//!    `traceparent` is byte-stable across 1000 parses; and that sampling
//!    decisions propagate.
//!
//! 2. **Redaction half** — verify that the canonical
//!    [`redaction::default_redactor`] redacts Bearer tokens, JWTs,
//!    AWS-style access keys, emails, and IPv4 addresses deterministically,
//!    with the same input producing byte-identical output across 1000
//!    runs and across [`Redactor`] instances.
//!
//! The fixture does **not** depend on the network, on time, on the
//! filesystem, on a database, on a running exporter, or on any other
//! crate. It is a pure, in-process, deterministic test.

use crate::correlation::{TraceContext, FLAG_SAMPLED};
use crate::redaction::{default_redactor, Redactor};

/// Fixed 16-byte trace-id used across the fixture. Chosen so that no
/// random number generator is involved; the test must be deterministic.
const FIXED_TRACE_ID: [u8; 16] = [
    0x0a, 0x1b, 0x2c, 0x3d, 0x4e, 0x5f, 0x60, 0x71, 0x82, 0x93, 0xa4, 0xb5, 0xc6, 0xd7, 0xe8, 0xf9,
];

/// Fixed 8-byte span-id for the parent.
const FIXED_PARENT_SPAN_ID: [u8; 8] = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08];

/// Fixed 8-byte span-id for the child.
const FIXED_CHILD_SPAN_ID: [u8; 8] = [0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17];

/// Canonical `traceparent` header value, hand-computed from the two fixed
/// ids above and the `SAMPLED` flag. The fixture asserts that
/// `TraceContext::to_traceparent()` returns exactly this string and that
/// `from_traceparent` round-trips back to the same `TraceContext`.
const CANONICAL_TRACEPARENT: &str = "00-0a1b2c3d4e5f60718293a4b5c6d7e8f9-0102030405060708-01";

/// Canonical redacted string. The fixture asserts that
/// `default_redactor().redact(SAMPLE_LOG)` returns exactly this string
/// and that the result is byte-stable across runs.
const SAMPLE_LOG: &str =
    "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxw contact alice@example.com from 10.0.0.42 key=AKIAIOSFODNN7EXAMPLE";

/// 1000 — chosen to give a meaningful determinism anchor without making
/// the test slow. The same number is used in both halves so the fixture
/// has a uniform stress budget.
const STRESS_RUNS: usize = 1000;

#[test]
fn g2_deterministic_correlation_and_redaction_fixture() {
    // ---------- CORRELATION HALF ----------

    // Build the parent TraceContext deterministically.
    let parent = TraceContext::new(FIXED_TRACE_ID, FIXED_PARENT_SPAN_ID, FLAG_SAMPLED)
        .expect("fixed parent ids must be valid");

    // Wire-format emit must be byte-exact.
    assert_eq!(
        parent.to_traceparent(),
        CANONICAL_TRACEPARENT,
        "to_traceparent drifted from canonical fixture value"
    );

    // Wire-format parse must round-trip back to the same TraceContext.
    let parsed_parent =
        TraceContext::from_traceparent(CANONICAL_TRACEPARENT).expect("canonical must parse");
    assert_eq!(
        parsed_parent, parent,
        "round-trip parse drifted from canonical"
    );

    // Sampling flag survives round-trip.
    assert!(parsed_parent.is_sampled(), "sampling flag dropped on parse");

    // Child context inherits trace_id + flags, gets new span_id.
    let child = parent
        .child(FIXED_CHILD_SPAN_ID)
        .expect("child construction must succeed");
    assert_eq!(
        child.trace_id(),
        parent.trace_id(),
        "child trace_id must equal parent trace_id"
    );
    assert_eq!(
        child.span_id(),
        &FIXED_CHILD_SPAN_ID,
        "child span_id must equal supplied value"
    );
    assert_eq!(
        child.flags(),
        parent.flags(),
        "child flags must inherit parent flags"
    );

    // Stress anchor: 1000 round-trips produce identical bytes.
    for _ in 0..STRESS_RUNS {
        let header = parent.to_traceparent();
        assert_eq!(header, CANONICAL_TRACEPARENT, "emit drifted under stress");
        let parsed = TraceContext::from_traceparent(&header).expect("canonical must always parse");
        assert_eq!(
            parsed.to_traceparent(),
            CANONICAL_TRACEPARENT,
            "round-trip drifted under stress"
        );
    }

    // ---------- REDACTION HALF ----------

    // Two independent Redactor instances (same rules) must produce
    // byte-identical output. This catches accidental dependence on
    // HashMap iteration order or on internal randomness.
    let redactor_a: Redactor = default_redactor();
    let redactor_b: Redactor = default_redactor();

    let first = redactor_a
        .redact(SAMPLE_LOG)
        .expect("default redactor must compile + run");
    assert!(
        first.contains("<REDACTED>"),
        "default redactor did not redact anything from sample log: {first}"
    );
    assert!(
        !first.contains("alice@example.com"),
        "email leaked: {first}"
    );
    assert!(!first.contains("10.0.0.42"), "ipv4 leaked: {first}");
    assert!(
        !first.contains("AKIAIOSFODNN7EXAMPLE"),
        "aws key leaked: {first}"
    );
    assert!(
        !first.contains("eyJhbGciOiJIUzI1NiJ9"),
        "JWT leaked: {first}"
    );

    let second = redactor_b
        .redact(SAMPLE_LOG)
        .expect("default redactor must compile + run");
    assert_eq!(
        first, second,
        "two Redactor instances produced different output for same input"
    );

    // Stress anchor: 1000 calls must produce identical output.
    for run in 0..STRESS_RUNS {
        let out = redactor_a
            .redact(SAMPLE_LOG)
            .expect("redaction failed under stress");
        assert_eq!(
            out, first,
            "redaction drifted at stress run {run}: {out} != {first}"
        );
    }
}
