use super::*;

fn sample_origin() -> RequestOrigin {
    RequestOrigin {
        hostname: "h".into(),
        process: "p".into(),
        pid: 1,
        callback: None,
    }
}

#[test]
fn new_fills_request_id_and_timestamps() {
    let spec = crate::spec::PromptSpec {
        title: "t".into(),
        question: "?".into(),
        field: crate::spec::FieldSpec::Boolean {
            label: "?".into(),
            default: Some(true),
        },
        notes: None,
        buttons: None,
        urgency: crate::spec::Urgency::Info,
        timeout_secs: 60,
        request_id: None,
    };
    let req = PendingRequest::new(spec.clone(), sample_origin());
    assert!(!req.request_id.is_empty());
    assert!(req.expires_at_ms > req.queued_at_ms);
    assert!(!req.is_terminal());

    let mut spec2 = spec;
    spec2.request_id = Some("my-id".into());
    let req2 = PendingRequest::new(spec2, sample_origin());
    assert_eq!(req2.request_id, "my-id");
}

#[test]
fn path_in_is_stable() {
    let req = PendingRequest {
        request_id: "abc".into(),
        origin: sample_origin(),
        spec: crate::spec::PromptSpec {
            title: "t".into(),
            question: "?".into(),
            field: crate::spec::FieldSpec::Boolean {
                label: "?".into(),
                default: None,
            },
            notes: None,
            buttons: None,
            urgency: crate::spec::Urgency::Info,
            timeout_secs: 60,
            request_id: Some("abc".into()),
        },
        queued_at_ms: 0,
        expires_at_ms: u64::MAX,
        state: RequestState::Pending,
        response: None,
        notified_via: vec![],
        metadata: serde_json::Map::new(),
    };
    let dir = Path::new("/x/inbox");
    assert_eq!(req.path_in(dir), PathBuf::from("/x/inbox/abc.json"));
}

#[test]
fn enqueue_and_load_roundtrip() {
    let tmp = tempfile::tempdir().unwrap();
    let req = PendingRequest {
        request_id: "rt-1".into(),
        origin: sample_origin(),
        spec: crate::spec::PromptSpec {
            title: "t".into(),
            question: "?".into(),
            field: crate::spec::FieldSpec::Boolean {
                label: "?".into(),
                default: Some(false),
            },
            notes: None,
            buttons: None,
            urgency: crate::spec::Urgency::Info,
            timeout_secs: 60,
            request_id: Some("rt-1".into()),
        },
        queued_at_ms: unix_now_ms(),
        expires_at_ms: unix_now_ms() + 60_000,
        state: RequestState::Pending,
        response: None,
        notified_via: vec![],
        metadata: serde_json::Map::new(),
    };
    enqueue(tmp.path(), &req).unwrap();
    let loaded = load(tmp.path(), "rt-1").unwrap();
    assert_eq!(loaded.request_id, "rt-1");
    assert_eq!(loaded.state, RequestState::Pending);
}

#[test]
fn finalize_moves_to_answered_dir() {
    let tmp = tempfile::tempdir().unwrap();
    let req = PendingRequest {
        request_id: "fn-1".into(),
        origin: sample_origin(),
        spec: crate::spec::PromptSpec {
            title: "t".into(),
            question: "?".into(),
            field: crate::spec::FieldSpec::Boolean {
                label: "?".into(),
                default: None,
            },
            notes: None,
            buttons: None,
            urgency: crate::spec::Urgency::Info,
            timeout_secs: 60,
            request_id: Some("fn-1".into()),
        },
        queued_at_ms: unix_now_ms(),
        expires_at_ms: unix_now_ms() + 60_000,
        state: RequestState::Answered,
        response: Some(ElicitResponse::Answered {
            value: crate::spec::FieldValue::Boolean(true),
            notes: None,
        }),
        notified_via: vec![],
        metadata: serde_json::Map::new(),
    };
    enqueue(tmp.path(), &req).unwrap();
    finalize(tmp.path(), &req).unwrap();
    let loaded = load(tmp.path(), "fn-1").unwrap();
    assert_eq!(loaded.state, RequestState::Answered);
}
