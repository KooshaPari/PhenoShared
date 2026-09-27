//! Form submission handling for the inbox daemon.
//!
//! This module handles POST requests from the HTML inbox form, parsing
//! URL-encoded or JSON form data and coercing it into the appropriate
//! `FieldValue` based on the request's `FieldSpec`.

use std::path::Path;

use serde::Deserialize;

use crate::{
    inbox::{expire_if_due, finalize, load, PendingRequest, RequestState},
    spec::{ElicitResponse, FieldSpec, FieldValue},
};

/// Why a form submission was refused.
///
/// The HTTP layer maps these onto status codes (409 / 400) instead of
/// collapsing every failure into a generic error string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum SubmitError {
    /// The request is past its TTL. A late POST must not record an answer —
    /// the TTL is authoritative even when no daemon is running to sweep it.
    Expired { expires_at_ms: u64 },
    /// The request is Answered / Cancelled / Expired. The first answer
    /// stands; a later POST must never rewrite it.
    AlreadyFinalized(RequestState),
    /// The body is missing something the spec requires, or is malformed.
    BadRequest(String),
}

impl std::fmt::Display for SubmitError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Expired {
                expires_at_ms,
            } => write!(
                f,
                "request expired at {expires_at_ms} ms since the epoch; a late answer is not \
                 recorded"
            ),
            Self::AlreadyFinalized(state) => write!(
                f,
                "request is already finalized (state={state:?}); the recorded answer stands"
            ),
            Self::BadRequest(msg) => f.write_str(msg),
        }
    }
}

impl std::error::Error for SubmitError {}

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
///
/// Refuses to record anything the human did not actually choose:
/// - a request that is already terminal is never re-answered;
/// - a body with no submit marker (`confirm` / `cancel`) is not a submission;
/// - a body that omits the field the spec asked for is not an answer.
pub(crate) fn submit_answer(
    inbox_root: &Path,
    request_id: &str,
    body: &[u8],
) -> Result<(), SubmitError> {
    // Accept both application/x-www-form-urlencoded and JSON.
    let body_str = std::str::from_utf8(body).map_err(|e| SubmitError::BadRequest(e.to_string()))?;
    let payload: FormPayload = if body_str.trim_start().starts_with('{') {
        serde_json::from_str(body_str).map_err(|e| SubmitError::BadRequest(e.to_string()))?
    } else {
        url_decode_form(body_str)
    };

    let mut req = match load(inbox_root, request_id) {
        Ok(r) => r,
        Err(e) => return Err(SubmitError::BadRequest(e.to_string())),
    };

    // Expiry is enforced here, not only by the daemon's notifier sweeper — a
    // daemon may not be running at all. The in-place transition mirrors what
    // the sweeper would have written, so the recorded state is the same.
    if expire_if_due(inbox_root, &mut req).map_err(|e| SubmitError::BadRequest(e.to_string()))? {
        return Err(SubmitError::Expired {
            expires_at_ms: req.expires_at_ms,
        });
    }

    // The first answer stands. `cli/answer.rs` and `inbox/ipc/server.rs` both
    // refuse to touch a terminal request; HTTP has to agree with them, or a
    // second POST silently rewrites the answer the human already gave.
    if req.is_terminal() {
        return Err(SubmitError::AlreadyFinalized(req.state));
    }

    // Validate the spec before processing — a stale / corrupt file
    // shouldn't take down the submit path.
    req.spec
        .validate()
        .map_err(|e| SubmitError::BadRequest(format!("invalid spec: {e}")))?;

    // Determine intent: an explicit `cancel=1` (Cancel button) wins over
    // `confirm=ok` (Submit button) because HTML forms submit the pressed
    // button's name+value, and a click on Cancel won't set confirm.
    let wants_cancel = payload.cancel.is_some() && payload.confirm.is_none();

    // Either button is a real submission; a body with neither is a partial or
    // truncated payload (or a stray request), and recording it would invent an
    // answer. The inbox form always sends one of them.
    if !wants_cancel && payload.confirm.is_none() {
        return Err(SubmitError::BadRequest(
            "missing submit marker: expected the form's 'confirm' (or 'cancel' to cancel)".into(),
        ));
    }

    // `notes` is a spec field like any other: when the spec marks it required,
    // the form's `required` attribute is a hint, not enforcement.
    if let Some(notes_spec) = &req.spec.notes {
        let supplied = payload.notes.as_deref().unwrap_or("");
        if notes_spec.required && supplied.trim().is_empty() {
            return Err(SubmitError::BadRequest(format!(
                "missing required notes: '{}'",
                notes_spec.label
            )));
        }
    }

    if wants_cancel {
        let notes = payload.notes.clone();
        finalize(
            inbox_root,
            &PendingRequest {
                state: RequestState::Cancelled,
                response: Some(ElicitResponse::Cancelled {
                    notes,
                }),
                ..req.clone()
            },
        )
        .map_err(|e| SubmitError::BadRequest(e.to_string()))?;
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
        finalize(inbox_root, &final_req).map_err(|e| SubmitError::BadRequest(e.to_string()))?;
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
            _ => {},
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
            },
            b'+' => {
                out.push(b' ');
                i += 1;
            },
            b => {
                out.push(b);
                i += 1;
            },
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
///
/// The field the spec asked for must be *present* in the body. An explicitly
/// empty string (`value=`) is a legitimate answer for the free-text kinds — a
/// human can genuinely intend `""` — but an absent key is not an answer at
/// all, and the two must not be conflated into a default.
pub(crate) fn coerce_field_value(
    field: &FieldSpec,
    payload: &FormPayload,
) -> Result<FieldValue, SubmitError> {
    match field {
        FieldSpec::Text {
            ..
        } => Ok(FieldValue::Text(required_value(payload)?)),
        FieldSpec::LongText {
            ..
        } => Ok(FieldValue::LongText(required_value(payload)?)),
        FieldSpec::Choice {
            options, ..
        } => {
            let raw = required_value(payload)?;
            let idx = options
                .iter()
                .position(|o| o.value == raw || o.label == raw)
                .ok_or_else(|| SubmitError::BadRequest(format!("choice '{raw}' not in options")))?;
            Ok(FieldValue::Choice {
                value: options[idx].value.clone(),
                index: idx,
            })
        },
        FieldSpec::Boolean {
            ..
        } => {
            // An unchecked HTML checkbox omits its key entirely, so absence
            // means `false`. The caller has already established that this is a
            // real submission (a submit marker was present).
            let v = payload.boolean.as_deref().unwrap_or("");
            match v {
                "true" | "on" | "1" | "yes" => Ok(FieldValue::Boolean(true)),
                "false" | "off" | "0" | "no" | "" => Ok(FieldValue::Boolean(false)),
                other => Err(SubmitError::BadRequest(format!(
                    "'{other}' is not a boolean"
                ))),
            }
        },
        FieldSpec::Integer {
            ..
        } => {
            let raw = payload
                .integer
                .clone()
                .or_else(|| payload.value.clone())
                .ok_or_else(|| missing("integer"))?;
            let n: i64 = raw
                .trim()
                .parse()
                .map_err(|e| SubmitError::BadRequest(format!("not an int: {e}")))?;
            Ok(FieldValue::Integer(n))
        },
        FieldSpec::DateTime {
            ..
        } => Ok(FieldValue::DateTime(required_value(payload)?)),
    }
}

/// Error for a field the spec asked for that the body did not carry.
fn missing(key: &str) -> SubmitError {
    SubmitError::BadRequest(format!(
        "missing required '{key}' field: the form did not carry a value"
    ))
}

/// Read the `value` key, distinguishing "absent" from "explicitly empty".
fn required_value(payload: &FormPayload) -> Result<String, SubmitError> {
    payload.value.clone().ok_or_else(|| missing("value"))
}

#[cfg(test)]
mod tests;
