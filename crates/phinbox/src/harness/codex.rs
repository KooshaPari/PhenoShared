use crate::{
    inbox::{enqueue, wait_for_response, PendingRequest, RequestOrigin, RequestState},
    spec::{ElicitResponse, FieldValue},
    ToolApproval,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::{
    path::Path,
    time::{Duration, Instant},
};

/// Current documented native Codex PermissionRequest input. Unknown fields fail closed.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct NativeRequest {
    cwd: String,
    hook_event_name: String,
    model: String,
    permission_mode: String,
    session_id: String,
    tool_input: Value,
    tool_name: String,
    transcript_path: Option<String>,
    turn_id: String,
    #[serde(default)]
    agent_id: Option<String>,
    #[serde(default)]
    agent_type: Option<String>,
}
fn decision(allow: bool, reason: &str) -> Value {
    json!({"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{
        "behavior":if allow{"allow"}else{"deny"},"message":reason}}})
}

/// Process one pending Codex PermissionRequest through the ordinary durable queue.
/// Always returns native deny JSON on errors, cancellation, expiry or non-boolean input.
/// Native hook registration/timeout and aggregation remain the harness's authority.
pub fn codex_permission_request(input: &[u8], root: &Path, timeout_secs: u64) -> Value {
    if input.len() > 1024 * 1024 || !(1..=120).contains(&timeout_secs) {
        return decision(
            false,
            "Phinbox refused oversized input or unsupported wait bound",
        );
    }
    let required = [
        "cwd",
        "hook_event_name",
        "model",
        "permission_mode",
        "session_id",
        "tool_input",
        "tool_name",
        "transcript_path",
        "turn_id",
    ];
    if !serde_json::from_slice::<Value>(input)
        .ok()
        .and_then(|v| {
            v.as_object()
                .map(|o| required.iter().all(|k| o.contains_key(*k)))
        })
        .unwrap_or(false)
    {
        return decision(
            false,
            "Phinbox refused incomplete native PermissionRequest input",
        );
    }
    let Ok(native) = serde_json::from_slice::<NativeRequest>(input) else {
        return decision(
            false,
            "Phinbox refused invalid native PermissionRequest input",
        );
    };
    if native.hook_event_name != "PermissionRequest"
        || native.session_id.is_empty()
        || native.turn_id.is_empty()
        || native.tool_name.is_empty()
        || native.cwd.is_empty()
        || !matches!(native.permission_mode.as_str(), "default" | "acceptEdits")
    {
        return decision(
            false,
            "Phinbox refused missing correlation or unsupported native permission mode",
        );
    }
    let mut approval=ToolApproval::new(&native.tool_name)
        .command(native.tool_input.to_string())
        .reason("Pending native Codex permission request. Existing harness policy still applies.")
        .fact("harness","codex").fact("session",&native.session_id)
        .fact("turn",&native.turn_id).fact("cwd",&native.cwd)
        .fact("model",&native.model).fact("permission_mode",&native.permission_mode)
        .warn("Only an explicit typed approval applies to this exact pending operation; workflow acknowledgment/closure is not permission.");
    if let Some(agent) = native.agent_id {
        approval = approval.fact("agent_id", agent);
    }
    if let Some(kind) = native.agent_type {
        approval = approval.fact("agent_type", kind);
    }
    // Transcript is provenance only. Never open the caller-supplied path.
    if let Some(path) = native.transcript_path {
        approval = approval.fact("transcript_path", path);
    }
    approval.timeout_secs = timeout_secs as u32;
    let mut spec = approval.to_prompt_spec();
    spec.request_id = Some(uuid::Uuid::new_v4().to_string());
    let request = PendingRequest::new(
        spec,
        RequestOrigin {
            hostname: std::env::var("HOSTNAME").unwrap_or_else(|_| "local".into()),
            process: "codex-permission-request".into(),
            pid: std::process::id(),
            callback: None,
        },
    );
    let start = Instant::now();
    if enqueue(root, &request).is_err() {
        return decision(false, "Phinbox could not persist permission request");
    }
    let Ok(answer) = wait_for_response(
        root,
        &request.request_id,
        Duration::from_millis(50),
        Duration::from_secs(timeout_secs),
    ) else {
        return decision(
            false,
            "Phinbox received no explicit approval before the bounded wait expired",
        );
    };
    let same = answer.request_id == request.request_id
        && answer.origin == request.origin
        && serde_json::to_value(&answer.spec).ok() == serde_json::to_value(&request.spec).ok();
    let allow = same
        && start.elapsed() < Duration::from_secs(timeout_secs)
        && answer.state == RequestState::Answered
        && matches!(
            answer.response,
            Some(ElicitResponse::Answered {
                value: FieldValue::Boolean(true),
                ..
            })
        );
    decision(
        allow,
        if allow {
            "Explicit approval received for this correlated pending request; native policy remains authoritative"
        } else {
            "Permission not approved: denied, cancelled, expired, deferred, invalid or mismatched response"
        },
    )
}
