//! Form detail page, field-widget renderer, and answer confirmation page.

use crate::inbox::PendingRequest;
use crate::spec::FieldSpec;

use super::super::css::full_html_css;
use super::super::helpers::{
    field_kind_label, format_age, html_attr, html_escape, unix_now_ms_diff, NAV_HTML,
};

// ---- form detail page ----

/// Render the form-widget HTML for a single [`FieldSpec`] variant.
///
/// Each variant emits the appropriate HTML input element:
/// - `Text` → `<input type=text|name=value …>`
/// - `LongText` → `<textarea name=value …>`
/// - `Integer` → `<input type=number name=integer …>`
/// - `Choice` → `<select name=value><option …>…</option></select>`
/// - `Boolean` → `<input type=checkbox name=boolean value=on …>`
/// - `DateTime` → `<input type=date|time|datetime-local name=value …>`
///
/// All user-controlled values (label, placeholder, default, choice labels)
/// pass through [`html_attr`] / [`html_escape`] before insertion.
#[must_use]
pub fn render_field_widget(field: &FieldSpec) -> String {
    match field {
        FieldSpec::Text {
            label,
            default,
            placeholder,
            max_length,
            secret,
            ..
        } => {
            let label_html = html_escape(label);
            let placeholder_html = placeholder
                .as_deref()
                .map(|p| format!(r#" placeholder="{}""#, html_attr(p)))
                .unwrap_or_default();
            let default_html = default
                .as_deref()
                .map(|d| format!(r#" value="{}""#, html_attr(d)))
                .unwrap_or_default();
            let max_len_html = max_length
                .map(|m| format!(r#" maxlength="{m}""#))
                .unwrap_or_default();
            let input_type = if *secret { "password" } else { "text" };
            format!(
                r"<label for=eli-field>{label_html}</label>\
                   <input id=eli-field type={input_type} name=value{placeholder_html}{default_html}{max_len_html} required>",
            )
        }
        FieldSpec::LongText {
            label,
            default,
            max_length,
        } => {
            let label_html = html_escape(label);
            let default_html = default
                .as_deref()
                .map(html_escape)
                .unwrap_or_default();
            let max_len_html = max_length
                .map(|m| format!(r#" maxlength="{m}""#))
                .unwrap_or_default();
            format!(
                r"<label for=eli-field>{label}</label>\
                   <textarea id=eli-field name=value{rows}{max_len}>{default}</textarea>",
                label = label_html,
                rows = r#" rows="4""#,
                max_len = max_len_html,
                default = default_html,
            )
        }
        FieldSpec::Integer {
            label,
            min,
            max,
            default,
        } => {
            let label_html = html_escape(label);
            let min_html = min.map(|m| format!(r#" min="{m}""#)).unwrap_or_default();
            let max_html = max.map(|m| format!(r#" max="{m}""#)).unwrap_or_default();
            let default_html = default
                .map(|d| format!(r#" value="{d}""#))
                .unwrap_or_default();
            format!(
                r"<label for=eli-field>{label_html}</label>\
                   <input id=eli-field type=number name=integer{min_html}{max_html}{default_html} required>",
            )
        }
        FieldSpec::Choice {
            label,
            options,
            default_index,
        } => {
            let label_html = html_escape(label);
            let mut opts = String::with_capacity(options.len() * 64);
            for (i, opt) in options.iter().enumerate() {
                let value = html_attr(&opt.value);
                let label_text = html_escape(&opt.label);
                let selected = default_index.is_some_and(|d| d == i);
                let sel_attr = if selected { " selected" } else { "" };
                opts.push_str(&format!(
                    r#"<option value="{value}"{sel_attr}>{label_text}</option>"#,
                ));
            }
            format!(
                r"<label for=eli-field>{label_html}</label>\
                   <select id=eli-field name=value required>{opts}</select>",
            )
        }
        FieldSpec::Boolean { label, default } => {
            let label_html = html_escape(label);
            let checked = default.unwrap_or(false);
            let checked_attr = if checked { " checked" } else { "" };
            format!(
                r"<label class=bool><input type=checkbox name=boolean value=on{checked_attr}> \
                   <span>{label_html}</span></label>",
            )
        }
        FieldSpec::DateTime {
            label,
            default,
            picker_kind,
        } => {
            use crate::spec::DateTimeKind;
            let input_type = match picker_kind {
                DateTimeKind::Date => "date",
                DateTimeKind::Time => "time",
                DateTimeKind::DateTime => "datetime-local",
            };
            let label_html = html_escape(label);
            let default_html = default
                .as_deref()
                .map(|d| format!(r#" value="{}""#, html_attr(d)))
                .unwrap_or_default();
            format!(
                r"<label for=eli-field>{label_html}</label>\
                   <input id=eli-field type={input_type} name=value{default_html} required>",
            )
        }
    }
}

/// Render a form detail page for one pending request.
///
/// The page emits a real `<form method=POST action=/inbox/{rid}/answer>`
/// with input/textarea/select/checkbox widgets per the [`FieldSpec`]
/// variant. Submitting POSTs the form back to the daemon's
/// `Route::Answer`, which validates, writes the JSON response file, and
/// redirects to `/inbox/{rid}/done`.
#[must_use]
pub fn render_form_html(req: &PendingRequest) -> String {
    let field_kind = field_kind_label(&req.spec.field);
    let urgency_badge = match req.spec.urgency {
        crate::spec::Urgency::Warning => " warn",
        crate::spec::Urgency::Error => " urgent",
        _ => "",
    };
    let ago = format_age(unix_now_ms_diff(req.queued_at_ms));
    let widget = render_field_widget(&req.spec.field);
    let notes_box = req
        .spec
        .notes
        .as_ref()
        .map(|n| {
            let req_attr = if n.required { " required" } else { "" };
            let max_len = n
                .max_length
                .map(|m| format!(r#" maxlength="{m}""#))
                .unwrap_or_default();
            format!(
                r"<label for=eli-notes>{nl}</label>\
                   <textarea id=eli-notes name=notes{req}{max_len}>{default}</textarea>",
                nl = html_escape(&n.label),
                req = req_attr,
                max_len = max_len,
                default = html_escape(n.default.as_deref().unwrap_or("")),
            )
        })
        .unwrap_or_default();
    format!(
        "<!doctype html><html lang=en>\
         <meta charset=utf-8>\
         <meta name=viewport content='width=device-width,initial-scale=1'>\
         <title>{title}</title>\
         <style>{css}</style>\
         <body>\
         {nav}\
         <div class=card{urg}><div class=row>\
         <div class=row-main><strong>{title}</strong>\
         <span class=ago>{ago}</span></div>\
         <div class=row-sub><span>{field_kind}</span></div></div></div>\
         <main class=card><h2>{question}</h2>\
         {widget}\
         {notes_box}\
         <form method=POST action=/inbox/{rid}/answer class=actions>\
         <button type=submit name=confirm value=ok class=ok>Submit</button>\
         <button type=submit name=cancel value=1 class=cancel>Cancel</button>\
         </form>\
         </main>\
         </body></html>",
        title = html_escape(req.spec.title.as_str()),
        css = full_html_css(),
        nav = NAV_HTML,
        urg = urgency_badge,
        rid = html_attr(&req.request_id),
        ago = ago,
        field_kind = field_kind,
        question = html_escape(&req.spec.question),
        widget = widget,
        notes_box = notes_box,
    )
}

// ---- answer confirmation page ----

/// Render a confirmation page after answering a request.
#[must_use]
pub fn render_answer_html(_request_id: &str, success: bool, message: &str) -> String {
    let icon = if success { "\u{2705}" } else { "\u{274C}" };
    let heading = if success {
        "Answer received"
    } else {
        "Failed to record answer"
    };
    format!(
        "<!doctype html><html lang=en>\
         <meta charset=utf-8>\
         <meta name=viewport content='width=device-width,initial-scale=1'>\
         <title>{icon} {heading}</title>\
         <style>{css}</style>\
         <body>\
         {nav}\
         <main class=card><h2>{icon} {heading}</h2>\
         <p>{message}</p>\
         <a href=/inbox class=ok>Return to inbox</a></main>\
         </body></html>",
        icon = icon,
        heading = heading,
        css = full_html_css(),
        nav = NAV_HTML,
        message = html_escape(message),
    )
}