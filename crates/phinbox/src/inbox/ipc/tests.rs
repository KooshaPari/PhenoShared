//! Tests for the JSON-RPC inbox server: the `inbox.answer` surface must
//! enforce expiry itself, not rely on the daemon's notifier sweeper.

use serde_json::json;

use super::*;
use crate::{
    error::ElicitError,
    inbox::{enqueue, inbox_pending_dir, load_request, RequestOrigin, RequestState},
    spec::{FieldSpec, PromptSpec, Urgency},
};

/// A request whose TTL is decades past, as it looks with no daemon
/// running to sweep it.
fn expired_request(id: &str) -> PendingRequest {
    let spec = PromptSpec {
        details: None,
        title: "Probe".into(),
        question: "?".into(),
        field: FieldSpec::Boolean {
            label: "Approve?".into(),
            default: None,
        },
        notes: None,
        buttons: None,
        urgency: Urgency::Info,
        timeout_secs: 60,
        request_id: Some(id.into()),
    };
    let mut req = PendingRequest::new(
        spec,
        RequestOrigin {
            hostname: "h".into(),
            process: "p".into(),
            pid: 1,
            callback: None,
        },
    );
    req.expires_at_ms = 1;
    req
}

/// Boot a real IPC server over `root` and return a connected client.
async fn server_and_client(
    root: &std::path::Path,
) -> (crate::inbox::ipc::Client, tokio::task::JoinHandle<()>) {
    let sock = crate::inbox::ipc::ipc_socket_path(root);
    let state = RpcState::new(root.to_path_buf(), sock.clone());
    let listener = bind_listener(&sock).await.expect("bind ipc socket");
    let server = spawn_accept(state, listener);
    (
        crate::inbox::ipc::Client::connect_to(sock).expect("connect ipc"),
        server,
    )
}

fn answer_params(id: &str, status: &str) -> Value {
    if status == "deferred" {
        return json!({
            "rid": id,
            "response": { "status": "deferred", "request_id": id },
        });
    }
    json!({
        "rid": id,
        "response": {
            "status": "answered",
            "value": { "kind": "boolean", "value": true },
        },
    })
}

/// `inbox.answer` must refuse an expired request with a distinct code and
/// must not archive it as answered — whether or not a sweeper is running.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn inbox_answer_refuses_an_expired_request() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    enqueue(&root, &expired_request("ipc-stale-1")).unwrap();
    assert_eq!(
        load_request(&root, "ipc-stale-1").unwrap().unwrap().state,
        RequestState::Pending,
        "precondition: genuinely unswept"
    );

    let (client, server) = server_and_client(&root).await;
    let err = client
        .call("inbox.answer", answer_params("ipc-stale-1", "answered"))
        .expect_err("an expired request must not be answerable");
    match err {
        ElicitError::Rpc {
            code,
            message,
        } => {
            assert_eq!(code, crate::inbox::ipc::ERR_EXPIRED, "message: {message}");
            assert!(message.contains("expired"), "message: {message}");
        },
        other => panic!("expected an RPC error, got {other:?}"),
    }
    server.abort();

    let after = load_request(&root, "ipc-stale-1")
        .unwrap()
        .expect("still on disk");
    assert_eq!(
        after.state,
        RequestState::Expired,
        "the TTL must settle the state"
    );
    assert!(after.response.is_none(), "no answer may be recorded");
    assert!(
        inbox_pending_dir(&root).join("ipc-stale-1.json").exists(),
        "an expired request stays in the inbox, it is not archived as answered"
    );
}

/// A defer is an answer attempt too: you cannot defer a closed window.
#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn inbox_answer_refuses_defer_on_an_expired_request() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    enqueue(&root, &expired_request("ipc-stale-2")).unwrap();

    let (client, server) = server_and_client(&root).await;
    let err = client
        .call("inbox.answer", answer_params("ipc-stale-2", "deferred"))
        .expect_err("deferring an expired request must be refused");
    assert!(
        matches!(err, ElicitError::Rpc { code, .. } if code == crate::inbox::ipc::ERR_EXPIRED),
        "got {err:?}"
    );
    server.abort();
    assert_eq!(
        load_request(&root, "ipc-stale-2").unwrap().unwrap().state,
        RequestState::Expired
    );
}
