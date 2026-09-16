//! Form submission handling for the inbox daemon.
//!
//! This module handles POST requests from the HTML inbox form, parsing
//! URL-encoded or JSON form data and coercing it into the appropriate
//! `FieldValue` based on the request's `FieldSpec`.

use std::path::Path;

use crate::inbox::{finalize, load, PendingRequest, RequestState};
use crate::spec::{ElicitResponse, FieldSpec, FieldValue};
use serde::Deserialize;

/// Deserialized form payload from the inbox submission.
#[derive(Debug, Deserialize)]
pub(crate) struct FormPayload {
    #[serde(default)]
    pub value: Option<String>,
    #[serde(default)]
    pub boolean: Option<String>,
    #[serde(default)]
    pub integer: Option<String>,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub cancel: Option<String>,
    #[serde(default)]
    pub confirm: Option<String>,
}

/// Submit an answer to a pending inbox request.
pub(crate) fn submit_answer(
    inbox_root: &Path,
    request_id: &str,
    body: &[u8],
) -> Result<(), String> {
    // Accept both application/x-www-form-urlencoded and JSON.
    let body_str = std::str::from_utf8(body).map_err(|e| e.to_string())?;
    let payload: FormPayload = if body_str.trim_start().starts_with('{') {
        serde_json::from_str(body_str).map_err(|e| e.to_string())?
    } else {
        url_decode_form(body_str)
    };

    let req = match load(inbox_root, request_id) {
        Ok(r) => r,
        Err(e) => return Err(e.to_string()),
    };

    // Validate the spec before processing — a stale / corrupt file
    // shouldn't take down the submit path.
    req.spec
        .validate()
        .map_err(|e| format!("invalid spec: {e}"))?;

    // Determine intent: an explicit `cancel=1` (Cancel button) wins over
    // `confirm=ok` (Submit button) because HTML forms submit the pressed
    // button's name+value, and a click on Cancel won't set confirm.
    let wants_cancel = payload.cancel.is_some() && payload.confirm.is_none();

    if wants_cancel {
        let notes = payload.notes.clone();
        finalize(
            inbox_root,
            &PendingRequest {
                state: RequestState::Cancelled,
                response: Some(ElicitResponse::Cancelled { notes }),
                ..req.clone()
            },
        )
        .map_err(|e| e.to_string())?;
    } else {
        let v = coerce_field_value(&req.spec.field, &payload)?;
        let response = ElicitResponse::Answered {
            value: v,
            notes: payload.notes,
        };
        let final_req = PendingRequest {
            state: RequestState::Answered,
            response: Some(response),
            ..req
        };
        finalize(inbox_root, &final_req).map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Parse a URL-encoded form body into a `FormPayload`.
pub(crate) fn url_decode_form(body: &str) -> FormPayload {
    let mut out = FormPayload {
        value: None,
        boolean: None,
        integer: None,
        notes: None,
        cancel: None,
        confirm: None,
    };
    for kv in body.split('&').filter(|s| !s.is_empty()) {
        let (k, v) = kv.split_once('=').unwrap_or((kv, ""));
        let v = url_decode(v);
        match k {
            "value" => out.value = Some(v),
            "boolean" => out.boolean = Some(v),
            "integer" => out.integer = Some(v),
            "notes" => out.notes = Some(v),
            "cancel" => out.cancel = Some(v),
            "confirm" => out.confirm = Some(v),
            _ => {}
        }
    }
    out
}

/// Decode a percent-encoded URL string.
pub(crate) fn url_decode(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        match bytes[i] {
            b'%' if i + 2 < bytes.len() => {
                let hi = hex(bytes[i + 1]);
                let lo = hex(bytes[i + 2]);
                if let (Some(h), Some(l)) = (hi, lo) {
                    out.push((h << 4) | l);
                    i += 3;
                } else {
                    out.push(b'%');
                    i += 1;
                }
            }
            b'+' => {
                out.push(b' ');
                i += 1;
            }
            b => {
                out.push(b);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// Convert a single hex character to its numeric value.
fn hex(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(b - b'a' + 10),
        b'A'..=b'F' => Some(b - b'A' + 10),
        _ => None,
    }
}

/// Coerce the raw form payload into a `FieldValue` matching the field spec.
pub(crate) fn coerce_field_value(
    field: &FieldSpec,
    payload: &FormPayload,
) -> Result<FieldValue, String> {
    match field {
        FieldSpec::Text { .. } => {
            let v = payload.value.clone().unwrap_or_default();
            Ok(FieldValue::Text(v))
        }
        FieldSpec::LongText { .. } => {
            let v = payload.value.clone().unwrap_or_default();
            Ok(FieldValue::LongText(v))
        }
        FieldSpec::Choice { options, .. } => {
            let raw = payload.value.clone().unwrap_or_default();
            let idx = options
                .iter()
                .position(|o| o.value == raw || o.label == raw)
                .ok_or_else(|| format!("choice '{raw}' not in options"))?;
            Ok(FieldValue::Choice {
                value: options[idx].value.clone(),
                index: idx,
            })
        }
        FieldSpec::Boolean { .. } => {
            let v = payload.boolean.as_deref().unwrap_or("");
            match v {
                "true" | "on" | "1" | "yes" => Ok(FieldValue::Boolean(true)),
                _ => Ok(FieldValue::Boolean(false)),
            }
        }
        FieldSpec::Integer { .. } => {
            let raw = payload
                .integer
                .clone()
                .or(payload.value.clone())
                .unwrap_or_default();
            let n: i64 = raw.trim().parse().map_err(|e| format!("not an int: {e}"))?;
            Ok(FieldValue::Integer(n))
        }
        FieldSpec::DateTime { .. } => {
            let raw = payload.value.clone().unwrap_or_default();
            Ok(FieldValue::DateTime(raw))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::inbox::RequestOrigin;
    use crate::inbox::unix_now_ms;

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
            Some(ElicitResponse::Answered { value, notes }) => {
                match value {
                    FieldValue::Choice { value: v, index } => {
                        assert_eq!(v, "staging");
                        assert_eq!(index, 0);
                    }
                    other => panic!("expected FieldValue::Choice, got {other:?}"),
                }
                assert_eq!(notes.as_deref(), Some("green build"));
            }
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
            Some(ElicitResponse::Cancelled { notes }) => {
                assert_eq!(notes.as_deref(), Some("on second thought"));
            }
            other => panic!("expected Cancelled response, got {other:?}"),
        }
    }
}
