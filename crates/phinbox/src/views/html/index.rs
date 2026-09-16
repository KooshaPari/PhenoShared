//! Inbox index page.

use crate::inbox::PendingRequest;

use super::super::css::full_html_css;
use super::super::helpers::{
    field_kind_label, format_age, html_attr, html_escape, truncate, unix_now_ms_diff,
    urgency_class, urgency_label, INBOX_SLUG,
};

#[must_use]
pub fn render_inbox_index_html(requests: &[PendingRequest]) -> String {
    let count = requests.len();
    if count == 0 {
        return format!(
            "<!doctype html><html lang=en>\
             <meta charset=utf-8>\
             <meta name=viewport content='width=device-width,initial-scale=1'>\
             <title>{title}</title>\
             <style>{css}</style>\
             <body>\
             <header><h1>{title}</h1></header>\
             <main class=empty><p>No pending requests</p>\
             <p>Use <code>phinbox ask</code> from your agent.</p></main>\
             <footer><p>phinbox</p></footer>\
             </body></html>",
            title = INBOX_SLUG,
            css = full_html_css(),
        );
    }
    let mut rows = String::with_capacity(count * 160);
    for req in requests {
        let urg = urgency_class(req.spec.urgency);
        let urgency_label = urgency_label(req.spec.urgency);
        let expired_class = if matches!(req.state, crate::inbox::RequestState::Expired) {
            " expired"
        } else {
            ""
        };
        let expired_badge = if matches!(req.state, crate::inbox::RequestState::Expired) {
            " <span class=badge>Expired</span>"
        } else {
            ""
        };
        rows.push_str(&format!(
            "<a href=/inbox/{rid} class=card {urg}{expired}><div class=row>\
             <div class=row-main><strong>{title}</strong>\
             <span class=ago>{ago}</span></div>\
             <div class=row-sub><span>{question}</span>\
             <span class=badge>{urgency_label}</span>\
             <span>{field_kind}</span>{expired_badge}</div></div></a>",
            rid = html_attr(&req.request_id),
            urg = urg,
            expired = expired_class,
            title = html_escape(req.spec.title.as_str()),
            ago = format_age(unix_now_ms_diff(req.queued_at_ms)),
            question = truncate(&html_escape(&req.spec.question), 80),
            urgency_label = urgency_label,
            field_kind = field_kind_label(&req.spec.field),
            expired_badge = expired_badge,
        ));
    }
    format!(
        "<!doctype html><html lang=en>\
         <meta charset=utf-8>\
         <meta name=viewport content='width=device-width,initial-scale=1'>\
         <title>{title}</title>\
         <style>{css}</style>\
         <body>\
         <header><h1>{title}</h1><span class=badge>{count}</span></header>\
         <main>{rows}</main>\
         <footer><p>phinbox</p></footer>\
         </body></html>",
        title = INBOX_SLUG,
        css = full_html_css(),
        count = count,
        rows = rows,
    )
}