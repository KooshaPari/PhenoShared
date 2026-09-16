//! Expired-request page.

use crate::inbox::PendingRequest;

use super::super::css::full_html_css;
use super::super::helpers::{
    field_kind_label, format_age, html_escape, unix_now_ms_diff, NAV_HTML,
};

// ---- expired request page ----

/// Render an expired-request page showing the request details with an
/// "expired" notice and no answer form.
#[must_use]
pub fn render_expired_html(req: &PendingRequest) -> String {
    let field_kind = field_kind_label(&req.spec.field);
    let urgency_badge = match req.spec.urgency {
        crate::spec::Urgency::Warning => " warn",
        crate::spec::Urgency::Error => " urgent",
        _ => "",
    };
    let ago = format_age(unix_now_ms_diff(req.queued_at_ms));
    format!(
        "<!doctype html><html lang=en>\
         <meta charset=utf-8>\
         <meta name=viewport content='width=device-width,initial-scale=1'>\
         <title>Expired: {title}</title>\
         <style>{css}</style>\
         <body>\
         {nav}\
         <div class=card expired{urg}><div class=row>\
         <div class=row-main><strong>{title}</strong>\
         <span class=ago>{ago}</span></div>\
         <div class=row-sub><span>{field_kind}</span>\
         <span class=badge>Expired</span></div></div></div>\
         <main class=card>\
         <h2>{question}</h2>\
         <p class=expired-notice>This request has expired and can no longer be answered.</p>\
         <a href=/inbox class=ok>Return to inbox</a>\
         </main>\
         </body></html>",
        title = html_escape(req.spec.title.as_str()),
        css = full_html_css(),
        nav = NAV_HTML,
        urg = urgency_badge,
        ago = ago,
        field_kind = field_kind,
        question = html_escape(&req.spec.question),
    )
}