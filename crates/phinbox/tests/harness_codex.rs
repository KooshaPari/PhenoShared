//! Real durable request/answer fixtures for the documented native Codex wire protocol.
#[path = "../src/harness/codex.rs"]
mod native_bridge;
use native_bridge::codex_permission_request;
pub use phinbox::{inbox, spec, ToolApproval};
use phinbox::{
    inbox::{finalize, PendingRequest, RequestState},
    spec::{ElicitResponse, FieldValue},
};
use serde_json::{json, Value};
use std::{
    path::Path,
    thread,
    time::{Duration, Instant},
};
fn input() -> Value {
    json!({"cwd":"/isolated/synthetic","hook_event_name":"PermissionRequest","model":"fixture",
    "permission_mode":"default","session_id":"fixture-session","tool_input":{"command":"printf synthetic"},
    "tool_name":"shell","transcript_path":null,"turn_id":"fixture-turn"})
}
fn wait_request(root: &Path) -> PendingRequest {
    let end = Instant::now() + Duration::from_secs(2);
    loop {
        if let Ok(entries) = std::fs::read_dir(root.join("inbox")) {
            for entry in entries.flatten() {
                if entry.path().extension().is_some_and(|e| e == "json") {
                    if let Ok(req) = serde_json::from_slice(&std::fs::read(entry.path()).unwrap()) {
                        return req;
                    }
                }
            }
        }
        assert!(Instant::now() < end, "bridge did not persist request");
        thread::sleep(Duration::from_millis(5));
    }
}
fn roundtrip(response: ElicitResponse, mutate: bool) -> Value {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    let wait = root.clone();
    let worker = thread::spawn(move || {
        codex_permission_request(&serde_json::to_vec(&input()).unwrap(), &wait, 3)
    });
    let mut req = wait_request(&root);
    req.state = RequestState::Answered;
    req.response = Some(response);
    if mutate {
        req.spec.question = "changed operation".into();
    }
    finalize(&root, &req).unwrap();
    worker.join().unwrap()
}
fn behavior(v: &Value) -> &str {
    v["hookSpecificOutput"]["decision"]["behavior"]
        .as_str()
        .unwrap()
}
#[test]
fn only_explicit_correlated_boolean_true_allows() {
    let out = roundtrip(
        ElicitResponse::Answered {
            value: FieldValue::Boolean(true),
            notes: None,
        },
        false,
    );
    assert_eq!(behavior(&out), "allow");
    assert_eq!(
        out["hookSpecificOutput"]["hookEventName"],
        "PermissionRequest"
    );
    assert!(out["hookSpecificOutput"]["decision"]
        .get("updatedPermissions")
        .is_none());
}
#[test]
fn boolean_false_and_text_true_and_defer_never_allow() {
    for response in [
        ElicitResponse::Answered {
            value: FieldValue::Boolean(false),
            notes: None,
        },
        ElicitResponse::Answered {
            value: FieldValue::Text("true".into()),
            notes: None,
        },
        ElicitResponse::Deferred {
            request_id: "unrelated".into(),
            open_url: None,
            path: None,
        },
        ElicitResponse::Cancelled { notes: None },
    ] {
        assert_eq!(behavior(&roundtrip(response, false)), "deny");
    }
}
#[test]
fn changed_pending_operation_cannot_reuse_approval() {
    assert_eq!(
        behavior(&roundtrip(
            ElicitResponse::Answered {
                value: FieldValue::Boolean(true),
                notes: None
            },
            true
        )),
        "deny"
    );
}
#[test]
fn malformed_unknown_or_native_noninteractive_mode_fails_closed_without_queue() {
    let tmp = tempfile::tempdir().unwrap();
    for payload in [
        json!({}),
        json!({"hook_event_name":"PreToolUse"}),
        {
            let mut i = input();
            i["permission_mode"] = json!("bypassPermissions");
            i
        },
        {
            let mut i = input();
            i["prior_policy_decision"] = json!("deny");
            i
        },
    ] {
        assert_eq!(
            behavior(&codex_permission_request(
                &serde_json::to_vec(&payload).unwrap(),
                tmp.path(),
                1
            )),
            "deny"
        );
    }
    assert!(!tmp.path().join("inbox").exists());
}
#[test]
fn management_acknowledgment_and_close_do_not_answer_permission() {
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    let wait = root.clone();
    let worker = thread::spawn(move || {
        codex_permission_request(&serde_json::to_vec(&input()).unwrap(), &wait, 1)
    });
    let req = wait_request(&root);
    let store = phinbox::management::Store::open(root.join("management.sqlite")).unwrap();
    store.observe_inbox(&root).unwrap();
    let id = format!("inbox:{}", req.request_id);
    let item = store.get(&id).unwrap().unwrap();
    store
        .apply(phinbox::management::Command {
            event_id: "synthetic-close".into(),
            item_id: id,
            expected_revision: item.revision,
            actor: "fixture".into(),
            action: phinbox::management::Action::Close,
        })
        .unwrap();
    assert_eq!(behavior(&worker.join().unwrap()), "deny");
}

#[test]
fn native_protocol_roundtrip_through_real_local_daemon_http_body() {
    use std::io::{Read, Write};
    let tmp = tempfile::tempdir().unwrap();
    let root = tmp.path().to_path_buf();
    let daemon = phinbox::inbox::daemon::start_daemon(phinbox::inbox::daemon::DaemonConfig {
        inbox_root: root.clone(),
        port: 0,
        bind: "127.0.0.1".parse().unwrap(),
        notify: phinbox::NotifyChannels::default(),
        enable_tray: false,
    })
    .unwrap();
    let wait = root.clone();
    let worker = thread::spawn(move || {
        codex_permission_request(&serde_json::to_vec(&input()).unwrap(), &wait, 3)
    });
    let request = wait_request(&root);
    let body = "confirm=1&boolean=true";
    let mut socket = std::net::TcpStream::connect(("127.0.0.1", daemon.port)).unwrap();
    socket
        .set_read_timeout(Some(Duration::from_secs(2)))
        .unwrap();
    write!(socket,"POST /answer/{} HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",request.request_id,daemon.port,body.len(),body).unwrap();
    socket.shutdown(std::net::Shutdown::Write).unwrap();
    let mut response = String::new();
    socket.read_to_string(&mut response).unwrap();
    assert!(
        response.starts_with("HTTP/1.1 302")
            || response.starts_with("HTTP/1.1 303")
            || response.starts_with("HTTP/1.1 200"),
        "{response}"
    );
    assert_eq!(behavior(&worker.join().unwrap()), "allow");
    daemon.stop().unwrap();
}
