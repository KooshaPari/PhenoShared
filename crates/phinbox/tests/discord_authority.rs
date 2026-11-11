//! Workflow management is never an elicitation answer or permission approval.
use phinbox::{
    inbox::{enqueue, finalize, load, PendingRequest, RequestOrigin, RequestState},
    management::{Action, Command, Status, Store},
    spec::{ElicitResponse, FieldSpec, FieldValue, Urgency},
    ToolApproval,
};

fn request(id: &str) -> PendingRequest {
    let mut spec = ToolApproval::new("dangerous-operation")
        .question("Allow the operation?\nKeep the original context intact.")
        .to_prompt_spec();
    spec.request_id = Some(id.into());
    PendingRequest::new(
        spec,
        RequestOrigin {
            hostname: "test-host".into(),
            process: "harness-permission".into(),
            pid: 9,
            callback: None,
        },
    )
}

#[test]
fn ack_assignment_defer_and_close_leave_real_permission_bytes_unchanged() {
    let tmp = tempfile::tempdir().unwrap();
    let inbox = tmp.path().join("inbox-root");
    let req = request("permission");
    let pending_path = enqueue(&inbox, &req).unwrap();
    let original_bytes = std::fs::read(&pending_path).unwrap();
    let db = tmp.path().join("management.db");
    let store = Store::open(&db).unwrap();
    store.observe_inbox(&inbox).unwrap();
    let mut item = store.get("inbox:permission").unwrap().unwrap();

    for (event, action) in [
        ("ack", Action::Ack),
        ("assign", Action::Assign("staff:7".into())),
        ("defer", Action::Defer),
        ("close", Action::Close),
    ] {
        item = store
            .apply(Command {
                event_id: event.into(),
                item_id: item.id.clone(),
                expected_revision: item.revision,
                actor: "operator:42".into(),
                action,
            })
            .unwrap();
        assert_eq!(
            std::fs::read(&pending_path).unwrap(),
            original_bytes,
            "{event} mutated permission source"
        );
        let permission = load(&inbox, "permission").unwrap();
        assert_eq!(permission.state, RequestState::Pending);
        assert!(
            permission.response.is_none(),
            "workflow action cannot supply an approval response"
        );
        assert!(!inbox.join("answered/permission.json").exists());
    }
    assert_eq!(item.status, Status::Closed);
    drop(store);
    let reopened = Store::open(&db).unwrap();
    reopened.observe_inbox(&inbox).unwrap();
    assert_eq!(reopened.get(&item.id).unwrap().unwrap(), item);
    assert_eq!(std::fs::read(pending_path).unwrap(), original_bytes);
}

#[test]
fn observer_detects_an_external_terminal_write_without_disclosing_the_answer() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("queue");
    let mut req = request("external");
    enqueue(&root, &req).unwrap();
    let store = Store::open(tmp.path().join("management.db")).unwrap();
    store.observe_inbox(&root).unwrap();
    let initial = store.get("inbox:external").unwrap().unwrap();
    assert_eq!(initial.status, Status::Open);

    req.state = RequestState::Answered;
    req.response = Some(ElicitResponse::Answered {
        value: FieldValue::Boolean(true),
        notes: Some("ANSWER-NEVER-PUBLISH-7a4f".into()),
    });
    let source_path = finalize(&root, &req).unwrap();
    let bytes = std::fs::read(&source_path).unwrap();
    let independent_reader = Store::open(store.path()).unwrap();
    independent_reader.observe_inbox(&root).unwrap();
    let closed = store.get(&initial.id).unwrap().unwrap();
    assert_eq!(closed.status, Status::Closed);
    assert_eq!(closed.original, initial.original);
    let projection = serde_json::to_string(&store.pending_effects(100).unwrap()).unwrap();
    assert!(!projection.contains("ANSWER-NEVER-PUBLISH-7a4f"));
    assert_eq!(std::fs::read(source_path).unwrap(), bytes);
    let count = store.pending_effects(100).unwrap().len();
    independent_reader.observe_inbox(&root).unwrap();
    assert_eq!(store.pending_effects(100).unwrap().len(), count);
}

#[test]
fn secret_prompts_remain_visible_as_restricted_pointers_without_content() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("queue");
    let mut urgent = request("secret-urgency");
    urgent.spec.urgency = Urgency::Secret;
    urgent.spec.title = "SECRET-TITLE-CONTENT".into();
    urgent.spec.question = "SECRET-URGENCY-CONTENT".into();
    let mut field = request("secret-field");
    field.spec.field = FieldSpec::Text {
        label: "Token".into(),
        default: Some("SECRET-TEXT-DEFAULT".into()),
        placeholder: None,
        max_length: None,
        secret: true,
        pattern: None,
    };
    let a = enqueue(&root, &urgent).unwrap();
    let b = enqueue(&root, &field).unwrap();
    let originals = (std::fs::read(&a).unwrap(), std::fs::read(&b).unwrap());
    let store = Store::open(tmp.path().join("management.db")).unwrap();
    store.observe_inbox(&root).unwrap();
    let items = store.list().unwrap();
    assert_eq!(
        items.len(),
        2,
        "restricted requests must remain operator-visible"
    );
    assert!(items.iter().all(|i| i.status == Status::Blocked));
    assert!(items.iter().all(|i| i.source_request_id.is_some()));
    let payload = serde_json::to_string(&store.pending_effects(100).unwrap()).unwrap();
    for secret in [
        "SECRET-TITLE-CONTENT",
        "SECRET-URGENCY-CONTENT",
        "SECRET-TEXT-DEFAULT",
    ] {
        assert!(!payload.contains(secret), "secret source leaked: {secret}");
    }
    assert!(items
        .iter()
        .all(|i| i.original.contains("local Phinbox inbox")));
    assert_eq!(std::fs::read(a).unwrap(), originals.0);
    assert_eq!(std::fs::read(b).unwrap(), originals.1);
}

#[test]
fn observer_sees_another_process_finalize_without_mutating_source() {
    const CHILD_ROOT: &str = "PHINBOX_DISCORD_TEST_CHILD_QUEUE";
    if let Some(root) = std::env::var_os(CHILD_ROOT) {
        // Re-enter only this test in a child test process. No global test
        // environment is mutated; the parent supplies the variable to Command.
        let root = std::path::PathBuf::from(root);
        let mut req = load(&root, "cross-process").unwrap();
        assert_eq!(req.state, RequestState::Pending);
        req.state = RequestState::Cancelled;
        req.response = Some(ElicitResponse::Cancelled { notes: None });
        let path = finalize(&root, &req).unwrap();
        assert!(path.exists());
        assert_eq!(
            load(&root, "cross-process").unwrap().state,
            RequestState::Cancelled
        );
        return;
    }
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("queue");
    enqueue(&root, &request("cross-process")).unwrap();
    let store = Store::open(tmp.path().join("management.db")).unwrap();
    store.observe_inbox(&root).unwrap();
    assert_eq!(
        store.get("inbox:cross-process").unwrap().unwrap().status,
        Status::Open
    );
    let child = std::process::Command::new(std::env::current_exe().unwrap())
        .args([
            "--exact",
            "observer_sees_another_process_finalize_without_mutating_source",
            "--nocapture",
        ])
        .env(CHILD_ROOT, &root)
        .output()
        .unwrap();
    assert!(
        child.status.success(),
        "child failed: {}",
        String::from_utf8_lossy(&child.stderr)
    );
    let path = root.join("answered/cross-process.json");
    let source_bytes = std::fs::read(&path).unwrap();
    store.observe_inbox(&root).unwrap();
    assert_eq!(
        store.get("inbox:cross-process").unwrap().unwrap().status,
        Status::Closed
    );
    assert_eq!(std::fs::read(path).unwrap(), source_bytes);
}

#[test]
fn expiry_closes_workflow_without_fabricating_a_harness_response() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("queue");
    let mut req = request("expired");
    req.expires_at_ms = 0;
    let source = enqueue(&root, &req).unwrap();
    let original = std::fs::read(&source).unwrap();
    let store = Store::open(tmp.path().join("management.db")).unwrap();
    store.observe_inbox(&root).unwrap();
    assert_eq!(
        store.get("inbox:expired").unwrap().unwrap().status,
        Status::Closed
    );
    assert_eq!(std::fs::read(source).unwrap(), original);
    let permission = load(&root, "expired").unwrap();
    assert_eq!(permission.state, RequestState::Pending);
    assert!(permission.response.is_none());
    assert!(!root.join("answered/expired.json").exists());
}

#[test]
fn observer_preserves_full_safe_approval_details_but_not_answer_notes_or_metadata() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().join("queue");
    let mut spec = ToolApproval::new("publish")
        .question("Publish this exact candidate?\nSecond line: \u{03bb}")
        .reason("Reviewed candidate reason")
        .command("publish --candidate exact-sha")
        .effect("Updates one public artifact")
        .file(
            "docs/report.pdf",
            phinbox::spec::FileAction::Write,
            Some("reviewed".into()),
        )
        .to_prompt_spec();
    spec.request_id = Some("safe-details".into());
    let expected = serde_json::to_value(&spec).unwrap();
    let mut req = PendingRequest::new(
        spec,
        RequestOrigin {
            hostname: "test".into(),
            process: "test".into(),
            pid: 1,
            callback: None,
        },
    );
    req.response = Some(ElicitResponse::Deferred {
        request_id: "safe-details".into(),
        open_url: None,
        path: None,
    });
    req.metadata
        .insert("private".into(), serde_json::json!("NEVER-MIRROR-METADATA"));
    enqueue(&root, &req).unwrap();
    let store = Store::open(tmp.path().join("ledger.db")).unwrap();
    store.observe_inbox(&root).unwrap();
    let item = store.get("inbox:safe-details").unwrap().unwrap();
    assert_eq!(
        serde_json::from_str::<serde_json::Value>(&item.original).unwrap(),
        expected
    );
    assert!(item.original.contains("publish --candidate exact-sha"));
    assert!(item.original.contains("docs/report.pdf"));
    assert!(item.original.contains("Reviewed candidate reason"));
    assert!(item.original.contains("Updates one public artifact"));
    assert!(!item.original.contains("NEVER-MIRROR-METADATA"));
    assert!(!item.original.contains("\"response\""));
    assert!(!item.original.contains("\"open_url\""));
}
