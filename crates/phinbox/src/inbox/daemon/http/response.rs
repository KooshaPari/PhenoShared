//! HTTP response helpers and HTML rendering for the daemon's inbox pages.

use std::io::Write;
use std::net::TcpStream;

use crate::inbox::PendingRequest;

/// Write a raw HTTP response with the given status, content-type, and body.
pub(crate) fn write_response(
    stream: &mut TcpStream,
    status: u16,
    reason: &str,
    content_type: &str,
    body: &[u8],
) -> std::io::Result<()> {
    write!(
        stream,
        "HTTP/1.1 {status} {reason}\r\nContent-Length: {}\r\nConnection: close\r\nContent-Type: {content_type}\r\n\r\n",
        body.len()
    )?;
    stream.write_all(body)?;
    stream.flush()?;
    Ok(())
}

/// Write a 302 redirect to `location` and return `None` so the caller
/// doesn't accidentally fall through to the default 200 path.
pub(crate) fn redirect_response(
    stream: &mut TcpStream,
    location: &str,
) -> std::io::Result<Option<String>> {
    let body = format!(
        "<!doctype html><meta charset=utf-8><title>redirecting</title>\
         <body><p>Redirecting to <a href=\"{location}\">{location}</a>...</p>"
    );
    write!(
        stream,
        "HTTP/1.1 302 Found\r\nLocation: {loc}\r\nContent-Length: {}\r\nConnection: close\r\nContent-Type: text/html; charset=utf-8\r\n\r\n",
        body.len(),
        loc = location
    )?;
    stream.write_all(body.as_bytes())?;
    stream.flush()?;
    Ok(None)
}

/// Build a simple text-status page.
pub(crate) fn simple_text(_status: u16, msg: &str) -> String {
    format!(
        "<!doctype html><meta charset=utf-8><title>phinbox</title>\
         <body style=\"font-family:system-ui;margin:2rem\">\
         <h1>phinbox</h1><p>{msg}</p>"
    )
}

/// Wrap raw HTML body for return.
pub(crate) fn text_response(_status: u16, body: &str) -> String {
    body.to_string()
}

// ---- HTML rendering for the daemon's own form pages ----

/// Render the inbox form HTML for a pending request.
pub(crate) fn render_inbox_html(req: &PendingRequest) -> String {
    use crate::views::render_form_html;
    let body = render_form_html(req);
    let title = html_escape(&req.spec.title);
    let question = html_escape(&req.spec.question);
    format!(
        "<!doctype html><meta charset=utf-8><title>{title}</title>\
         <style>{css}</style><body>\
         <div class=card>\
           <h1>{title}</h1><p class=q>{question}</p>\
           <p class=meta>From <code>{origin}</code> on <code>{host}</code> . queued {queued}</p>\
           {body}\
         </div>",
        title = title,
        css = render_inbox_css(),
        question = question,
        origin = html_escape(&req.origin.process),
        host = html_escape(&req.origin.hostname),
        queued = format_relative_time(req.queued_at_ms),
        body = body,
    )
}

/// Inline CSS for the daemon's inbox UI.
pub(crate) fn render_inbox_css() -> &'static str {
    "body{background:#0f172a;color:#f8fafc;font-family:system-ui;margin:0;padding:2rem}\
     .card{max-width:640px;margin:auto;background:#1e293b;border-radius:12px;padding:2rem;\
     box-shadow:0 8px 24px rgba(0,0,0,.4)}\
     h1{margin:0 0 .5rem}p.q{white-space:pre-wrap;color:#cbd5e1}\
     p.meta{color:#64748b;font-size:.85rem;margin:0 0 1.5rem}\
     label{display:block;margin:1rem 0 .25rem;font-weight:600}\
     input[type=text],input[type=number],textarea,select{width:100%;padding:.6rem;\
     border-radius:8px;background:#0f172a;color:#f8fafc;border:1px solid #334155;font-size:1rem}\
     textarea{min-height:6rem}\
     button{padding:.7rem 1.4rem;border-radius:8px;border:none;font-weight:600;\
     cursor:pointer;margin-right:.5rem}\
     .ok{background:#22c55e;color:#052e16}.cancel{background:#ef4444;color:#fff}\
     .secret{background:#facc15;color:#1c1917}"
}

/// Escape HTML special characters.
pub(crate) fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

/// Format a UNIX millisecond timestamp as a human-readable relative time.
pub(crate) fn format_relative_time(ms: u64) -> String {
    let now = crate::inbox::unix_now_ms();
    let delta = now.saturating_sub(ms);
    if delta < 60_000 {
        return format!("{delta}s ago");
    }
    if delta < 3_600_000 {
        return format!("{}m ago", delta / 60_000);
    }
    if delta < 86_400_000 {
        return format!("{}h ago", delta / 3_600_000);
    }
    format!("{}d ago", delta / 86_400_000)
}
