//! Webhook notification backend.
//!
//! POSTs a JSON payload to a generic webhook URL (NTFY, Pushover,
//! Slack incoming webhook, etc.). Uses a raw TCP socket to avoid
//! pulling in `reqwest`.

use super::{inbox_open_url, NotifyAttempt};
use crate::inbox::{NotificationKind, PendingRequest};

/// POST a JSON payload to a webhook URL (NTFY, Pushover, Slack).
#[must_use]
pub fn notify_webhook(req: &PendingRequest, url: &str) -> NotifyAttempt {
    let payload = serde_json::json!({
        "title": req.spec.title,
        "question": req.spec.question,
        "request_id": req.request_id,
        "open_url": inbox_open_url(req),
    });
    let json = match serde_json::to_string(&payload) {
        Ok(s) => s,
        Err(e) => {
            return NotifyAttempt::err(NotificationKind::Webhook, format!("serialize: {e}"));
        }
    };
    match post_form(url, &json) {
        Ok(()) => NotifyAttempt::ok(NotificationKind::Webhook, "ok"),
        Err(e) => NotifyAttempt::err(NotificationKind::Webhook, e),
    }
}

/// Best-effort HTTP POST of a JSON body. We don't pull in `reqwest`
/// just for this -- a raw TCP write to the host parsed from the URL is
/// enough for the small NTFY-style payloads we send. If the URL is
/// unreachable, the inbox still works, so the failure is fine.
fn post_form(url: &str, body: &str) -> Result<(), String> {
    use std::io::Write;
    use std::net::TcpStream;
    use std::time::Duration;

    let stripped = url
        .strip_prefix("http://")
        .or_else(|| url.strip_prefix("https://"))
        .ok_or_else(|| "only http(s) URLs are supported".to_string())?;
    let (authority, path) = match stripped.split_once('/') {
        Some((a, p)) => (a, format!("/{p}")),
        None => (stripped, "/".into()),
    };
    let default_port = if url.starts_with("https://") { 443 } else { 80 };
    let (host, port) = match authority.rsplit_once(':') {
        Some((h, p)) => (h.to_string(), p.parse::<u16>().unwrap_or(default_port)),
        None => (authority.to_string(), default_port),
    };
    let addr = format!("{host}:{port}");

    let mut stream =
        TcpStream::connect(&addr).map_err(|e| format!("connect {addr}: {e}"))?;
    stream
        .set_write_timeout(Some(Duration::from_secs(3)))
        .map_err(|e| format!("set timeout: {e}"))?;

    let req = format!(
        "POST {path} HTTP/1.1\r\n\
         Host: {host}\r\n\
         Content-Type: application/json\r\n\
         Content-Length: {len}\r\n\
         Connection: close\r\n\
         \r\n\
         {body}",
        path = path,
        host = host,
        len = body.len(),
        body = body,
    );
    stream
        .write_all(req.as_bytes())
        .map_err(|e| format!("write: {e}"))?;
    Ok(())
}
