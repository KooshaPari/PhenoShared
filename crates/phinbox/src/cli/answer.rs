//! `phinbox answer` subcommand implementation.

use std::path::PathBuf;

use phinbox::inbox::{finalize, RequestState};
use phinbox::spec::{ElicitResponse, FieldSpec, FieldValue};
use serde_json::json;

/// Submit an answer to a queued inbox request via the CLI (no UI).
#[derive(Debug, clap::Args)]
pub struct AnswerArgs {
    /// The request ID to answer.
    #[arg(long)]
    pub request_id: String,
    /// Text value (for text, long-text, choice, or date-time fields).
    #[arg(long)]
    pub value: Option<String>,
    /// Integer value.
    #[arg(long)]
    pub integer: Option<i64>,
    /// Boolean value.
    #[arg(long)]
    pub boolean: Option<bool>,
    /// Cancel instead of answering.
    #[arg(long)]
    pub cancel: bool,
    /// Optional notes.
    #[arg(long)]
    pub notes: Option<String>,
}

pub fn cmd_answer(args: AnswerArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    let mut req = phinbox::inbox::load(inbox_dir, &args.request_id)
        .map_err(|e| e.to_string())?;

    // Expiry is authoritative here, not only in the daemon's sweeper: an
    // expired request must not be answerable when no daemon is up to reap it.
    // Transition it in place first (mirroring the sweeper) so the on-disk
    // state does not depend on whether a daemon happens to be running.
    if phinbox::inbox::expire_if_due(inbox_dir, &mut req).map_err(|e| e.to_string())? {
        return Err(format!(
            "request {} expired at {} ms since the epoch (now {} ms) and can no longer be answered",
            req.request_id,
            req.expires_at_ms,
            phinbox::inbox::unix_now_ms()
        ));
    }

    if req.is_terminal() {
        return Err(format!(
            "request {} is already in terminal state {:?}",
            req.request_id, req.state
        ));
    }

    let response = if args.cancel {
        ElicitResponse::Cancelled {
            notes: args.notes.clone(),
        }
    } else if let Some(n) = args.integer {
        ElicitResponse::Answered {
            value: FieldValue::Integer(n),
            notes: args.notes.clone(),
        }
    } else if let Some(b) = args.boolean {
        ElicitResponse::Answered {
            value: FieldValue::Boolean(b),
            notes: args.notes.clone(),
        }
    } else if let Some(v) = args.value {
        let value = match &req.spec.field {
            FieldSpec::Text { .. } => FieldValue::Text(v),
            FieldSpec::LongText { .. } => FieldValue::LongText(v),
            FieldSpec::Choice { options, .. } => {
                let idx = options
                    .iter()
                    .position(|o| o.value == v || o.label == v)
                    .ok_or_else(|| format!("choice '{v}' not in options"))?;
                FieldValue::Choice {
                    value: options[idx].value.clone(),
                    index: idx,
                }
            }
            FieldSpec::DateTime { .. } => FieldValue::DateTime(v),
            _ => return Err("use --integer or --boolean for this field type".into()),
        };
        ElicitResponse::Answered {
            value,
            notes: args.notes.clone(),
        }
    } else {
        return Err("one of --value / --integer / --boolean / --cancel is required".into());
    };

    req.state = match response {
        ElicitResponse::Cancelled { .. } => RequestState::Cancelled,
        _ => RequestState::Answered,
    };
    req.response = Some(response.clone());

    finalize(inbox_dir, &req).map_err(|e| e.to_string())?;
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "status": "submitted",
            "request_id": req.request_id,
            "response": response,
        }))
        .map_err(|e| e.to_string())?
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use phinbox::inbox::{
        answered_dir, enqueue, load, PendingRequest, RequestOrigin, RequestState,
    };
    use phinbox::spec::{ElicitResponse, FieldSpec, PromptSpec, Urgency};

    fn pending(id: &str, expires_at_ms: u64) -> PendingRequest {
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
        req.expires_at_ms = expires_at_ms;
        req
    }

    fn answer_args(id: &str, cancel: bool) -> AnswerArgs {
        AnswerArgs {
            request_id: id.into(),
            value: None,
            integer: None,
            boolean: Some(true),
            cancel,
            notes: None,
        }
    }

    /// Reproduces the reported defect: with no daemon sweeping, a request
    /// whose `expires_at_ms` is decades in the past was answered and archived.
    #[test]
    fn expired_request_is_refused_and_not_archived() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path().to_path_buf();
        enqueue(&root, &pending("stale-1", 1)).unwrap();

        let err = cmd_answer(answer_args("stale-1", false), &root).unwrap_err();
        assert!(err.contains("expired"), "refusal must name the expiry: {err}");

        let after = load(&root, "stale-1").unwrap();
        assert_eq!(after.state, RequestState::Expired);
        assert!(after.response.is_none(), "no answer may be recorded");
        assert!(
            !answered_dir(&root).join("stale-1.json").exists(),
            "an expired request must not be archived as answered"
        );
    }

    /// `--cancel` is an answer attempt too.
    #[test]
    fn expired_request_cannot_be_cancelled_via_cli() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path().to_path_buf();
        enqueue(&root, &pending("stale-2", 1)).unwrap();
        let err = cmd_answer(answer_args("stale-2", true), &root).unwrap_err();
        assert!(err.contains("expired"), "got {err}");
        assert_eq!(load(&root, "stale-2").unwrap().state, RequestState::Expired);
    }

    /// The defer affordance keeps working: a deferred-but-live request is
    /// still answerable, and it is answered (not refused) while its TTL holds.
    #[test]
    fn deferred_request_with_a_live_ttl_is_still_answerable() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path().to_path_buf();
        let mut req = pending("defer-1", phinbox::inbox::unix_now_ms() + 60_000);
        req.response = Some(ElicitResponse::Deferred {
            request_id: "defer-1".into(),
            open_url: None,
            path: None,
        });
        enqueue(&root, &req).unwrap();

        cmd_answer(answer_args("defer-1", false), &root).unwrap();
        let after = load(&root, "defer-1").unwrap();
        assert_eq!(after.state, RequestState::Answered);
        assert!(matches!(
            after.response,
            Some(ElicitResponse::Answered { .. })
        ));
    }

    /// A request whose TTL has passed cannot be deferred either.
    #[test]
    fn expiry_is_settled_on_disk_even_for_the_unswept_case() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path().to_path_buf();
        enqueue(&root, &pending("stale-3", 1)).unwrap();
        // Precondition: still `pending`, i.e. genuinely unswept.
        assert_eq!(load(&root, "stale-3").unwrap().state, RequestState::Pending);
        let _ = cmd_answer(answer_args("stale-3", false), &root);
        assert_eq!(
            load(&root, "stale-3").unwrap().state,
            RequestState::Expired,
            "the refusal must settle the state the sweeper would have written"
        );
    }
}
