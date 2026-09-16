//! HTML page renderers for the inbox web frontend.
//!
//! ## Submodules
//!
//! - `form` -- form detail page, field-widget renderer, answer confirmation
//! - `expired` -- expired-request page
//! - `index` -- inbox index page

mod expired;
mod form;
mod index;

pub use expired::render_expired_html;
pub use form::{render_answer_html, render_field_widget, render_form_html};
pub use index::render_inbox_index_html;

use crate::inbox::PendingRequest;
use crate::spec::FieldSpec;

use super::css::full_html_css;
use super::helpers::{field_kind_label, html_escape};

// ---- generic helpers ----

// ---- generic helpers ----

/// Render a full-page HTML document around content.
#[must_use]
pub fn render_full_html(title: &str, content: &str) -> String {
    format!(
        "<!doctype html><html lang=en>\
         <meta charset=utf-8>\
         <meta name=viewport content='width=device-width,initial-scale=1'>\
         <title>{title}</title>\
         <style>{css}</style>\
         <body>{content}</body></html>",
        title = html_escape(title),
        css = full_html_css(),
        content = content,
    )
}

/// Render plain-text summary of a pending request.
#[must_use]
pub fn render_plain_text(req: &PendingRequest) -> String {
    let field_kind = field_kind_label(&req.spec.field);
    format!(
        "[{kind}] {title}: {question}",
        kind = field_kind,
        title = req.spec.title.as_str(),
        question = req.spec.question,
    )
}

/// Render a one-line summary string for a pending request.
#[must_use]
pub fn render_summary(req: &PendingRequest) -> String {
    format!(
        "{} — {} ({})",
        req.spec.title,
        req.spec.question,
        field_kind_label(&req.spec.field),
    )
}

/// Render a JSON summary for a pending request.
#[must_use]
pub fn render_summary_json(req: &PendingRequest) -> serde_json::Value {
    let field_kind = match &req.spec.field {
        FieldSpec::Text { .. } => "text",
        FieldSpec::LongText { .. } => "long_text",
        FieldSpec::Integer { .. } => "integer",
        FieldSpec::Choice { .. } => "choice",
        FieldSpec::Boolean { .. } => "boolean",
        FieldSpec::DateTime { .. } => "date_time",
    };
    serde_json::json!({
        "request_id": req.request_id,
        "title": &req.spec.title,
        "question": req.spec.question,
        "field_kind": field_kind,
        "queued_at_ms": req.queued_at_ms,
    })
}
