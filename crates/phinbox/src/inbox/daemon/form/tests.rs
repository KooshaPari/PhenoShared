//! Unit tests for the inbox daemon form-submission path.

use super::*;
use crate::inbox::{unix_now_ms, RequestOrigin};

#[test]
fn form_decode_parses_simple() {
    let f = url_decode_form("value=hello+world&notes=ok");
    assert_eq!(f.value.as_deref(), Some("hello world"));
    assert_eq!(f.notes.as_deref(), Some("ok"));
}

/// v0.7.0 end-to-end: POST a form-encoded body to `submit_answer`,
/// confirm the request moves to `Answered` in `answered/` with the
/// captured `FieldValue`, and confirm the cancel button flips to
/// `Cancelled` with notes preserved.
#[test]
fn post_handler_writes_answer() {
    let tmp = tempfile::tempdir().unwrap();
    let origin = RequestOrigin {
        hostname: "h".into(),
        process: "p".into(),
        pid: 1,
        callback: None,
    };
    let req = PendingRequest {
        request_id: "post-1".into(),
        origin,
        spec: crate::spec::PromptSpec {
            details: None,
            title: "Choose".into(),
            question: "Pick env".into(),
            field: FieldSpec::Choice {
                label: "env".into(),
                options: vec![
                    crate::spec::ChoiceOption {
                        value: "staging".into(),
                        label: "Staging".into(),
                        description: None,
                    },
                    crate::spec::ChoiceOption {
                        value: "prod".into(),
                        label: "Production".into(),
                        description: None,
                    },
                ],
                default_index: None,
            },
            notes: Some(crate::spec::NotesSpec {
                label: "Why?".into(),
                default: None,
                max_length: None,
                required: false,
            }),
            buttons: None,
            urgency: crate::spec::Urgency::Warning,
            timeout_secs: 60,
            request_id: Some("post-1".into()),
        },
        queued_at_ms: unix_now_ms(),
        expires_at_ms: unix_now_ms() + 60_000,
        state: RequestState::Pending,
        response: None,
        notified_via: vec![],
        metadata: serde_json::Map::new(),
    };
    crate::inbox::enqueue(tmp.path(), &req).unwrap();

    let body = b"value=staging&notes=green+build&confirm=ok";
    submit_answer(tmp.path(), "post-1", body).expect("submit_answer ok");
    let loaded = load(tmp.path(), "post-1").unwrap();
    assert_eq!(loaded.state, RequestState::Answered);
    match loaded.response {
        Some(ElicitResponse::Answered {
            value,
            notes,
        }) => {
            match value {
                FieldValue::Choice {
                    value: v,
                    index,
                } => {
                    assert_eq!(v, "staging");
                    assert_eq!(index, 0);
                },
                other => panic!("expected FieldValue::Choice, got {other:?}"),
            }
            assert_eq!(notes.as_deref(), Some("green build"));
        },
        other => panic!("expected Answered response, got {other:?}"),
    }
    assert!(!tmp.path().join("inbox/post-1.json").exists());
    assert!(tmp.path().join("answered/post-1.json").exists());

    // 2. Cancel path
    let req2 = PendingRequest {
        request_id: "post-2".into(),
        origin: RequestOrigin {
            hostname: "h".into(),
            process: "p".into(),
            pid: 1,
            callback: None,
        },
        spec: crate::spec::PromptSpec {
            details: None,
            title: "Approve?".into(),
            question: "?".into(),
            field: FieldSpec::Boolean {
                label: "?".into(),
                default: None,
            },
            notes: None,
            buttons: None,
            urgency: crate::spec::Urgency::Info,
            timeout_secs: 60,
            request_id: Some("post-2".into()),
        },
        queued_at_ms: unix_now_ms(),
        expires_at_ms: unix_now_ms() + 60_000,
        state: RequestState::Pending,
        response: None,
        notified_via: vec![],
        metadata: serde_json::Map::new(),
    };
    crate::inbox::enqueue(tmp.path(), &req2).unwrap();
    let body = b"cancel=1&notes=on+second+thought";
    submit_answer(tmp.path(), "post-2", body).expect("cancel ok");
    let loaded2 = load(tmp.path(), "post-2").unwrap();
    assert_eq!(loaded2.state, RequestState::Cancelled);
    match loaded2.response {
        Some(ElicitResponse::Cancelled {
            notes,
        }) => {
            assert_eq!(notes.as_deref(), Some("on second thought"));
        },
        other => panic!("expected Cancelled response, got {other:?}"),
    }
}

/// Build a pending request from a spec, with a fixed request id.
fn pending(id: &str, field: FieldSpec, notes: Option<crate::spec::NotesSpec>) -> PendingRequest {
    PendingRequest {
        request_id: id.into(),
        origin: RequestOrigin {
            hostname: "h".into(),
            process: "p".into(),
            pid: 1,
            callback: None,
        },
        spec: crate::spec::PromptSpec {
            details: None,
            title: "Name".into(),
            question: "?".into(),
            field,
            notes,
            buttons: None,
            urgency: crate::spec::Urgency::Info,
            timeout_secs: 60,
            request_id: Some(id.into()),
        },
        queued_at_ms: unix_now_ms(),
        expires_at_ms: unix_now_ms() + 60_000,
        state: RequestState::Pending,
        response: None,
        notified_via: vec![],
        metadata: serde_json::Map::new(),
    }
}

fn text_field() -> FieldSpec {
    FieldSpec::Text {
        label: "Name".into(),
        default: None,
        placeholder: None,
        max_length: None,
        secret: false,
        pattern: None,
    }
}

/// A request whose TTL is long past, as it looks when no daemon has been
/// running to sweep it (the sweeper only runs while a daemon is up).
fn pending_expired(id: &str) -> PendingRequest {
    PendingRequest {
        expires_at_ms: 1,
        ..pending(id, text_field(), None)
    }
}

/// The load-bearing case for "expiry must not depend on a daemon being up":
/// an expired-but-unswept request is not answerable, and the attempt settles
/// the state in place exactly as the sweeper would have, so an observer
/// cannot tell which of the two wrote `Expired`.
#[test]
fn expired_request_is_refused_without_a_daemon() {
    let tmp = tempfile::tempdir().unwrap();
    crate::inbox::enqueue(tmp.path(), &pending_expired("stale-1")).unwrap();
    // Precondition: still `pending` on disk, i.e. genuinely unswept.
    assert_eq!(
        load(tmp.path(), "stale-1").unwrap().state,
        RequestState::Pending
    );

    let err = submit_answer(tmp.path(), "stale-1", b"value=late&confirm=ok").unwrap_err();
    assert!(
        matches!(
            err,
            SubmitError::Expired {
                expires_at_ms: 1
            }
        ),
        "a late POST must be refused as expired, got {err:?}"
    );

    let after = load(tmp.path(), "stale-1").unwrap();
    assert_eq!(
        after.state,
        RequestState::Expired,
        "the refusal must settle the state the sweeper would have written"
    );
    assert!(after.response.is_none(), "no answer may be recorded");
    assert!(
        !crate::inbox::answered_dir(tmp.path())
            .join("stale-1.json")
            .exists(),
        "an expired request must not be archived as answered"
    );
}

/// Cancel is an answer attempt too, and a fresh request is unaffected.
#[test]
fn expired_request_cannot_be_cancelled_and_fresh_requests_still_answer() {
    let tmp = tempfile::tempdir().unwrap();
    crate::inbox::enqueue(tmp.path(), &pending_expired("stale-2")).unwrap();
    assert!(matches!(
        submit_answer(tmp.path(), "stale-2", b"cancel=1"),
        Err(SubmitError::Expired { .. })
    ));
    assert_eq!(
        load(tmp.path(), "stale-2").unwrap().state,
        RequestState::Expired
    );

    // Control: the same path with a live TTL still records the answer.
    crate::inbox::enqueue(tmp.path(), &pending("fresh-1", text_field(), None)).unwrap();
    submit_answer(tmp.path(), "fresh-1", b"value=ok&confirm=ok").unwrap();
    assert_eq!(
        load(tmp.path(), "fresh-1").unwrap().state,
        RequestState::Answered
    );
}

/// v0.9.1: a body with no submit marker, or without the field the spec
/// asked for, is not an answer; and the first answer stands forever.
#[test]
fn submit_answer_rejects_partial_bodies_and_reanswers() {
    let tmp = tempfile::tempdir().unwrap();
    crate::inbox::enqueue(tmp.path(), &pending("guard-1", text_field(), None)).unwrap();

    // No submit marker: not a submission, even though a value is present.
    assert!(matches!(
        submit_answer(tmp.path(), "guard-1", b"value=x"),
        Err(SubmitError::BadRequest(_))
    ));
    // Submit marker but no field: nothing for the human to have chosen.
    assert!(matches!(
        submit_answer(tmp.path(), "guard-1", b"confirm=ok"),
        Err(SubmitError::BadRequest(_))
    ));
    assert!(matches!(
        submit_answer(tmp.path(), "guard-1", b""),
        Err(SubmitError::BadRequest(_))
    ));
    let untouched = load(tmp.path(), "guard-1").unwrap();
    assert_eq!(untouched.state, RequestState::Pending);
    assert!(untouched.response.is_none());

    // The first real answer lands.
    submit_answer(tmp.path(), "guard-1", b"value=alice&confirm=ok").unwrap();
    // A later POST is refused outright and changes nothing.
    assert_eq!(
        submit_answer(tmp.path(), "guard-1", b"value=bob&confirm=ok"),
        Err(SubmitError::AlreadyFinalized(RequestState::Answered))
    );
    match load(tmp.path(), "guard-1").unwrap().response {
        Some(ElicitResponse::Answered {
            value: FieldValue::Text(v),
            ..
        }) => assert_eq!(v, "alice", "the first answer must stand"),
        other => panic!("expected Answered(Text(\"alice\")), got {other:?}"),
    }
}

/// v0.9.1: an explicit empty text answer is legitimate; a body that omits
/// the key entirely is not. The two must not collapse into one default.
#[test]
fn submit_answer_distinguishes_empty_from_absent() {
    let tmp = tempfile::tempdir().unwrap();
    crate::inbox::enqueue(tmp.path(), &pending("guard-2", text_field(), None)).unwrap();

    submit_answer(tmp.path(), "guard-2", b"value=&confirm=ok").unwrap();
    match load(tmp.path(), "guard-2").unwrap().response {
        Some(ElicitResponse::Answered {
            value: FieldValue::Text(v),
            ..
        }) => assert!(v.is_empty(), "an explicit empty answer is a real answer"),
        other => panic!("expected Answered(Text(\"\")), got {other:?}"),
    }
}

/// v0.9.1: `notes.required` is enforced server-side, not just by the
/// form's `required` attribute.
#[test]
fn submit_answer_enforces_required_notes() {
    let tmp = tempfile::tempdir().unwrap();
    let notes = crate::spec::NotesSpec {
        label: "Why?".into(),
        default: None,
        max_length: None,
        required: true,
    };
    crate::inbox::enqueue(tmp.path(), &pending("guard-3", text_field(), Some(notes))).unwrap();

    assert!(matches!(
        submit_answer(tmp.path(), "guard-3", b"value=x&confirm=ok"),
        Err(SubmitError::BadRequest(_))
    ));
    assert!(
        matches!(
            submit_answer(tmp.path(), "guard-3", b"value=x&notes=+&confirm=ok"),
            Err(SubmitError::BadRequest(_))
        ),
        "whitespace-only notes do not satisfy a required notes box"
    );
    submit_answer(tmp.path(), "guard-3", b"value=x&notes=why&confirm=ok").unwrap();
    match load(tmp.path(), "guard-3").unwrap().response {
        Some(ElicitResponse::Answered {
            notes, ..
        }) => {
            assert_eq!(notes.as_deref(), Some("why"));
        },
        other => panic!("expected Answered, got {other:?}"),
    }
}
