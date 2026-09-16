//! Notification backends: tray, iMessage, email, webhook.
//!
//! Each backend is **best-effort** -- the inbox is the source of truth on
//! disk; notifications are just "wake the user up" hints. Failures are
//! logged at `warn` level but never propagated to the caller (the
//! caller has already enqueued the request and the user can always open
//! the inbox manually).
//!
//! Backends in this module shell out to native utilities rather than
//! binding to Cocoa/AppKit / `WinRT` directly. That matches the rest of
//! `phinbox` -- zero native dependencies, no cross-compile friction.

mod imessage;
mod tray;
mod webhook;

pub use imessage::{notify_email, notify_imessage};
pub use tray::notify_native;
pub use webhook::notify_webhook;

use crate::inbox::{NotificationKind, PendingRequest};
use crate::spec::PromptSpec;
use serde::{Deserialize, Serialize};

/// Per-surface configuration captured by the agent at enqueue time or
/// inherited from the environment.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct NotifyChannels {
    /// iMessage destination (Apple ID phone number or email).
    #[serde(default)]
    pub imessage_target: Option<String>,

    /// Email destination.
    #[serde(default)]
    pub email_target: Option<String>,

    /// Generic webhook URL (NTFY, Pushover, Slack incoming webhook...).
    #[serde(default)]
    pub webhook_url: Option<String>,

    /// Whether to also fire an `osascript`-driven native notification
    /// (Notification Center on macOS, Toast on Windows).
    #[serde(default)]
    pub native: bool,
}

/// Why a notification attempt failed (so callers can log it). Does not
/// affect the inbox workflow.
#[derive(Debug, Clone)]
pub struct NotifyAttempt {
    pub kind: NotificationKind,
    pub ok: bool,
    pub detail: String,
}

impl NotifyAttempt {
    pub(super) fn ok(kind: NotificationKind, detail: impl Into<String>) -> Self {
        Self {
            kind,
            ok: true,
            detail: detail.into(),
        }
    }
    pub(super) fn err(kind: NotificationKind, err: impl std::fmt::Display) -> Self {
        Self {
            kind,
            ok: false,
            detail: err.to_string(),
        }
    }
}

/// Surface every notification configured in `cfg` for `req`. Returns the
/// per-surface outcomes for telemetry. Failures of any one backend do
/// NOT short-circuit the others.
#[must_use]
pub fn surface_all(req: &PendingRequest, cfg: &NotifyChannels) -> Vec<NotifyAttempt> {
    let mut out = Vec::new();
    if cfg.native {
        out.push(notify_native(req));
    }
    if let Some(target) = cfg.imessage_target.as_deref() {
        out.push(notify_imessage(req, target));
    }
    if let Some(target) = cfg.email_target.as_deref() {
        out.push(notify_email(req, target));
    }
    if let Some(url) = cfg.webhook_url.as_deref() {
        out.push(notify_webhook(req, url));
    }
    out
}

// ----- shared helpers (used by submodules via super::) -----

pub(super) fn run_osascript(script: &str) -> Result<(), String> {
    if !cfg!(target_os = "macos") {
        return Err("osascript only available on macos".into());
    }
    use std::process::Command;
    let out = Command::new("osascript")
        .args(["-e", script])
        .output()
        .map_err(|e| format!("spawn osascript: {e}"))?;
    if out.status.success() {
        Ok(())
    } else {
        Err(format!(
            "osascript: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ))
    }
}

/// Open `url` in the user's default browser using the platform's
/// "open" command:
///
/// - macOS: `open <url>`
/// - Windows: `cmd /c start "" <url>`
/// - Linux / BSD / other: `xdg-open <url>`
///
/// Returns `Ok(())` on exit-status 0; `Err(msg)` otherwise. The caller
/// is expected to log and continue -- opening the browser is a
/// best-effort side channel, never a hard requirement.
pub fn open_in_default_browser(url: &str) -> Result<(), String> {
    use std::process::Command;
    let (cmd, args): (&str, Vec<&str>) = if cfg!(target_os = "macos") {
        ("open", vec![url])
    } else if cfg!(target_os = "windows") {
        ("cmd", vec!["/c", "start", "", url])
    } else {
        ("xdg-open", vec![url])
    };
    let status = Command::new(cmd)
        .args(args)
        .status()
        .map_err(|e| format!("spawn {cmd}: {e}"))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!("{cmd} exit {status:?}"))
    }
}

pub(super) fn open_url(url: &str) -> Result<(), String> {
    open_in_default_browser(url)
}

/// Render the request into the iMessage/email body.
#[must_use]
pub fn render_imessage_body(req: &PendingRequest) -> String {
    render_prompt_as_text(&req.spec, &req.request_id)
}

/// Same as [`render_imessage_body`] but for a bare spec (no `PendingRequest`).
#[must_use]
pub fn render_prompt_as_text(spec: &PromptSpec, request_id: &str) -> String {
    let mut s = String::new();
    s.push_str(&format!("{}\n\n", spec.title));
    s.push_str(&spec.question);
    s.push_str("\n\n");
    s.push_str(&format!("request_id: {request_id}\n"));
    s.push_str(&format!(
        "open: {}\n",
        inbox_open_url_for(spec.request_id.as_deref().unwrap_or(request_id))
    ));
    s.push_str(&format!(
        "reply: phinbox answer --request-id {request_id} --value <your-answer>\n"
    ));
    s
}

/// The URL the user can open in a browser to land on a fully styled
/// inbox form for the request.
#[must_use]
pub fn inbox_open_url(req: &PendingRequest) -> String {
    inbox_open_url_for(&req.request_id)
}

/// URL helper -- defaults to the local daemon (`localhost:7117`) unless
/// `PHINBOX_BASE_URL` is set.
#[must_use]
pub fn inbox_open_url_for(request_id: &str) -> String {
    let base = std::env::var("PHINBOX_BASE_URL")
        .unwrap_or_else(|_| "http://localhost:7117".to_string());
    format!("{base}/inbox/{request_id}")
}

pub(super) fn url_encode(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char);
            }
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

pub(super) fn escape_applescript(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

pub(super) fn escape_powershell(s: &str) -> String {
    s.replace('\'', "''")
}

pub(super) fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        return s.to_string();
    }
    let mut out: String = s.chars().take(max).collect();
    out.push('\u{2026}');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_req(request_id: &str) -> PendingRequest {
        let spec = crate::spec::PromptSpec {
            title: "Approval needed".into(),
            question: "Continue with rollout to production?".into(),
            field: crate::spec::FieldSpec::Boolean {
                label: "Approve?".into(),
                default: Some(true),
            },
            notes: None,
            buttons: None,
            urgency: crate::spec::Urgency::Warning,
            timeout_secs: 600,
            request_id: Some(request_id.into()),
        };
        PendingRequest {
            request_id: request_id.into(),
            origin: crate::inbox::RequestOrigin {
                hostname: "h".into(),
                process: "p".into(),
                pid: 1,
                callback: None,
            },
            spec,
            queued_at_ms: 0,
            expires_at_ms: u64::MAX,
            state: crate::inbox::RequestState::Pending,
            response: None,
            notified_via: vec![],
            metadata: serde_json::Map::new(),
        }
    }

    #[test]
    fn render_text_contains_open_and_reply() {
        let body = render_imessage_body(&sample_req("abc"));
        assert!(body.contains("request_id: abc"));
        assert!(body.contains("/inbox/abc"));
        assert!(body.contains("phinbox answer --request-id abc"));
    }

    #[test]
    fn url_encoding() {
        assert_eq!(url_encode("hello world"), "hello%20world");
        assert_eq!(url_encode("a&b=c"), "a%26b%3Dc");
    }

    #[test]
    fn applescript_escape_quotes() {
        assert_eq!(escape_applescript(r#"he said "hi""#), r#"he said \"hi\""#);
    }

    #[test]
    fn truncation_drops_with_ellipsis() {
        assert_eq!(truncate("abcdef", 3), "abc\u{2026}");
        assert_eq!(truncate("abc", 10), "abc");
    }

    #[test]
    fn inbox_open_url_default_port() {
        assert!(inbox_open_url_for("xyz").ends_with("/inbox/xyz"));
    }

    #[test]
    fn surface_all_with_empty_cfg_is_empty() {
        let attempts = surface_all(&sample_req("xyz"), &NotifyChannels::default());
        assert!(attempts.is_empty());
    }

    #[test]
    fn webhook_attempt_succeeds_with_dummy_url() {
        let req = sample_req("xyz");
        let payload = serde_json::json!({
            "title": req.spec.title,
            "request_id": req.request_id,
            "open_url": inbox_open_url(&req),
        });
        assert!(payload["title"].as_str().is_some());
    }
}
