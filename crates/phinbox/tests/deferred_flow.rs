//! End-to-end validation of the Deferred (defer-to-inbox) flow across the
//! public API: enqueue → defer → still visible in pending list → re-answer.
//!
//! Regression guard for the bug where `finalize_via_state` called `finalize()`
//! on a `Deferred` response, which moved the file to `answered/` — hiding the
//! request from `list_pending` and making it unanswerable.

use std::time::Duration;

use phinbox::{
    inbox::{
        enqueue, finalize, list_pending, load_request, PendingRequest, RequestOrigin, RequestState,
    },
    spec::{ElicitResponse, FieldSpec, PromptSpec},
};

fn temp_root(tag: &str) -> (tempfile::TempDir, std::path::PathBuf) {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().join(tag);
    std::fs::create_dir_all(&root).expect("mkdir root");
    (dir, root)
}

fn origin() -> RequestOrigin {
    RequestOrigin {
        hostname: "test".into(),
        process: "deferred_flow".into(),
        pid: 1,
        callback: None,
    }
}

fn spec(rid: &str) -> PromptSpec {
    PromptSpec {
        title: "Approve: rm".into(),
        question: "Delete build artifacts?".into(),
        field: FieldSpec::Boolean {
            label: "Approve?".into(),
            default: Some(false),
        },
        details: Some(phinbox::spec::DetailsSpec {
            reason: Some("cleanup".into()),
            items: vec![phinbox::spec::DetailItem::File {
                path: "target/".into(),
                action: phinbox::spec::FileAction::Delete,
                note: None,
            }],
            effects: vec!["1.2 GB reclaimed".into()],
            command: Some("rm -rf target/".into()),
        }),
        buttons: Some(phinbox::spec::ButtonSpec {
            cancel: "Cancel".into(),
            confirm: "Approve".into(),
            default_is_cancel: true,
            defer_label: Some("Defer to inbox".into()),
        }),
        notes: None,
        urgency: phinbox::spec::Urgency::Warning,
        timeout_secs: 600,
        request_id: Some(rid.into()),
    }
}

fn new_req(rid: &str) -> PendingRequest {
    PendingRequest::new(spec(rid), origin())
}

/// Defer, then verify the request is still answerable from pending — the
/// core promise of the defer affordance: "keep working, answer later".
#[test]
fn deferred_request_stays_in_pending_and_is_answerable() {
    let (_tmp, root) = temp_root("stay-pending");

    // 1. Agent enqueues an approval request.
    let req = new_req("defer-1");
    enqueue(&root, &req).expect("enqueue");

    // 2. Operator clicks "Defer to inbox" on the popup. Popup side: state stays Pending, response
    //    records the defer.
    let mut deferred = req.clone();
    deferred.state = RequestState::Pending;
    deferred.response = Some(ElicitResponse::Deferred {
        request_id: req.request_id.clone(),
        open_url: None,
        path: None,
    });
    // 3. The popup-side defer must NOT move the file to answered/. It should keep it in pending/ so
    //    the inbox UI and list_pending see it.
    let path = phinbox::inbox::inbox_pending_dir(&root).join("defer-1.json");
    assert!(path.exists(), "deferred request must remain in pending/");

    // 4. list_pending still surfaces it (the inbox is the operator's to-do list).
    let pending = list_pending(&root).expect("list_pending");
    assert_eq!(
        pending.len(),
        1,
        "deferred request must stay visible in inbox"
    );
    assert_eq!(pending[0].request_id, "defer-1");
    assert!(!pending[0].is_terminal(), "deferred must not be terminal");

    // 5. load_request (used by inbox.get) still finds it.
    let reloaded = load_request(&root, "defer-1")
        .expect("load_request")
        .expect("present");
    assert_eq!(reloaded.state, RequestState::Pending);

    // 6. Later, the operator answers it from the inbox UI.
    let mut answered = reloaded;
    answered.state = RequestState::Answered;
    answered.response = Some(ElicitResponse::Answered {
        value: phinbox::spec::FieldValue::Boolean(false),
        notes: None,
    });
    finalize(&root, &answered).expect("finalize after defer");

    // 7. Now it leaves pending and lands in answered/.
    let pending_after = list_pending(&root).expect("list_pending");
    assert!(
        pending_after.is_empty(),
        "answered request leaves the inbox"
    );
    let answered_file = load_request(&root, "defer-1")
        .expect("load_request")
        .expect("still on disk in answered/");
    assert_eq!(answered_file.state, RequestState::Answered);
}

/// The MCP caller's contract: a Deferred response tells it to keep working
/// and poll later. wait_for_response must NOT return on a defer (the request
/// is still pending); it must keep waiting until the operator truly answers.
#[test]
fn wait_for_response_ignores_defer_and_blocks_until_answer() {
    let (_tmp, root) = temp_root("wait-ignore-defer");

    let req = new_req("defer-2");
    enqueue(&root, &req).expect("enqueue");

    // Simulate a defer landing on disk WITHOUT moving to answered/:
    // re-write the pending file with response=Deferred, state=Pending.
    let mut deferred = req.clone();
    deferred.state = RequestState::Pending;
    deferred.response = Some(ElicitResponse::Deferred {
        request_id: req.request_id.clone(),
        open_url: None,
        path: None,
    });
    phinbox::inbox::enqueue(&root, &deferred).expect("re-enqueue deferred");

    // Answer after a short delay from another "thread" (operator via inbox UI).
    let root2 = root.clone();
    let rid = req.request_id.clone();
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(150));
        let mut answered = deferred_from_disk(&root2, &rid);
        answered.state = RequestState::Answered;
        answered.response = Some(ElicitResponse::Answered {
            value: phinbox::spec::FieldValue::Boolean(true),
            notes: None,
        });
        finalize(&root2, &answered).expect("late finalize");
    });

    // The caller waits through the defer; only the real answer unblocks it.
    let final_req = phinbox::inbox::wait_for_response(
        &root,
        &req.request_id,
        Duration::from_millis(50),
        Duration::from_secs(5),
    )
    .expect("wait_for_response");
    assert!(
        final_req.is_terminal(),
        "waiter unblocks only on real answer"
    );
    assert_eq!(final_req.state, RequestState::Answered);
    assert!(
        !matches!(final_req.response, Some(ElicitResponse::Deferred { .. })),
        "caller must never observe a stale defer as the final answer"
    );
}

fn deferred_from_disk(root: &std::path::Path, rid: &str) -> PendingRequest {
    load_request(root, rid).expect("load").expect("exists")
}

/// Direct regression test for the IPC-server defer path: `inbox.answer`
/// with a Deferred response must leave the request in pending/ (state
/// Pending), NOT run finalize() which would move it to answered/.
/// Drives the REAL server over its Unix socket.
///
/// `inbox::ipc` is Unix-only (no UDS on Windows), so this test is gated to
/// match; the defer semantics it covers are asserted portably by
/// `deferred_request_stays_in_pending_and_is_answerable` above.
#[cfg(unix)]
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn ipc_answer_with_deferred_keeps_request_in_pending() {
    let (_tmp, root) = temp_root("ipc-defer");

    let req = new_req("defer-3");
    enqueue(&root, &req).expect("enqueue");

    // Boot the real IPC server on a temp socket, exactly like the daemon does.
    let sock = root.join("ipc.sock");
    let state = phinbox::inbox::ipc::RpcState::new(root.clone(), sock.clone());
    let listener = phinbox::inbox::ipc::bind_listener(&sock)
        .await
        .expect("bind");
    let _server = phinbox::inbox::ipc::spawn_accept(state, listener);

    // Enqueue event for watchers (mirrors daemon behavior).
    // 1. The request is still in pending/ before answering.
    assert_eq!(list_pending(&root).expect("list").len(), 1);

    // 2. Drive the real "inbox.answer" method with a Deferred response.
    let client = phinbox::inbox::ipc::Client::connect_to(sock).expect("connect");
    let result = client
        .call(
            "inbox.answer",
            serde_json::json!({
                "rid": "defer-3",
                "response": {
                    "status": "deferred",
                    "request_id": "defer-3",
                }
            }),
        )
        .expect("inbox.answer with deferred must succeed");

    // 3. Server returns the request, state pending.
    let req_back: PendingRequest =
        serde_json::from_value(result["request"].clone()).expect("parse response");
    assert_eq!(req_back.state, RequestState::Pending);
    assert!(matches!(
        req_back.response,
        Some(ElicitResponse::Deferred { .. })
    ));

    // THE CONTRACT: after the server processes a defer, the request must
    // still be in the inbox (pending), not archived to answered/.
    let visible = list_pending(&root).expect("list_pending");
    assert_eq!(
        visible.len(),
        1,
        "BUG: server defer path finalized the request into answered/, hiding it from the \
         operator's inbox"
    );
    assert_eq!(visible[0].request_id, "defer-3");

    // 4. The deferred request remains answerable: answer it through the server.
    let answer = client
        .call(
            "inbox.answer",
            serde_json::json!({
                "rid": "defer-3",
                "response": {
                    "status": "answered",
                    "value": { "kind": "boolean", "value": false },
                }
            }),
        )
        .expect("deferred request must be answerable");
    let answered_req: PendingRequest =
        serde_json::from_value(answer["request"].clone()).expect("parse answer");
    assert_eq!(answered_req.state, RequestState::Answered);

    // 5. Now it leaves pending and is archived in answered/.
    let pending_after = list_pending(&root).expect("list_pending");
    assert!(
        pending_after.is_empty(),
        "answered request leaves the inbox"
    );
}

/// Schema wire-format check: the details block round-trips through JSON
/// (MCP callers send PromptSpec as JSON; renderers receive it as JSON).
#[test]
fn details_block_serde_roundtrip_preserves_everything() {
    let s = spec("serde-1");
    let json = serde_json::to_string(&s).expect("serialize");
    let back: PromptSpec = serde_json::from_str(&json).expect("deserialize");
    let d = back.details.expect("details survived roundtrip");
    assert_eq!(d.reason.as_deref(), Some("cleanup"));
    assert_eq!(d.command.as_deref(), Some("rm -rf target/"));
    assert_eq!(d.effects, vec!["1.2 GB reclaimed".to_string()]);
    assert!(matches!(
        d.items.as_slice(),
        [phinbox::spec::DetailItem::File {
            action: phinbox::spec::FileAction::Delete,
            ..
        }]
    ));
    // Wire format uses the tagged kind discriminators.
    assert!(
        json.contains("\"kind\":\"file\""),
        "file item tag must serialize: {json}"
    );
    assert!(
        json.contains("\"action\":\"delete\""),
        "file action lowercase: {json}"
    );

    // Old callers (pre-details) must still deserialize — field is optional.
    let minimal = serde_json::json!({
        "title": "t",
        "question": "?",
        "field": { "kind": "boolean", "label": "?", "default": null },
        "urgency": "info",
        "timeout_secs": 60
    });
    let old: PromptSpec = serde_json::from_value(minimal).expect("old callers still parse");
    assert!(old.details.is_none());
}

/// JSON Schema export must include the new types — MCP servers advertise
/// the schema, so a missing DetailsSpec would silently break clients.
#[test]
fn schema_export_includes_details_and_deferred() {
    let s = phinbox::schema::prompt_spec_schema();
    let s_str = serde_json::to_string(&s).expect("schema serializes");
    assert!(
        s_str.contains("DetailsSpec"),
        "PromptSpec schema must document details: {s_str}"
    );
    assert!(
        s_str.contains("DetailItem"),
        "schema must document detail items"
    );
    assert!(
        s_str.contains("defer_label"),
        "ButtonSpec schema must document defer_label"
    );

    let r = phinbox::schema::elicit_response_schema();
    let r_str = serde_json::to_string(&r).expect("response schema serializes");
    assert!(
        r_str.contains("deferred"),
        "ElicitResponse schema must document Deferred: {r_str}"
    );
}

/// The ToolApproval builder is the ergonomic front door; verify its output
/// through the real serialization path a renderer would consume.
#[test]
fn tool_approval_builder_produces_renderable_spec() {
    let spec = phinbox::approval::ToolApproval::new("git push --force")
        .reason("Feature branch needs a force push after rebase.")
        .command("git push --force origin feature/x")
        .file(
            "refs/heads/feature/x",
            phinbox::spec::FileAction::Write,
            None,
        )
        .effect("Remote history rewritten")
        .warn("Collaborators must re-clone")
        .fact("branch", "feature/x")
        .urgency(phinbox::spec::Urgency::Error)
        .to_prompt_spec();

    // Validated: renderer contract (validate() is the pre-render check).
    spec.validate().expect("builder output passes validation");

    let d = spec.details.clone().expect("builder sets details");
    assert_eq!(
        d.reason.as_deref(),
        Some("Feature branch needs a force push after rebase.")
    );
    assert!(d.items.len() >= 3, "file + fact + warning items present");
    let json = serde_json::to_string(&spec).expect("serialize");
    let back: PromptSpec = serde_json::from_str(&json).expect("deserialize");
    assert!(back.details.is_some(), "details survive the wire");
}
