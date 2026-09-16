//! HTML escape/attr utilities, format helpers, and field/urgency label mappers.

use crate::spec::FieldSpec;

pub const INBOX_SLUG: &str = "phinbox inbox";
pub(crate) const NAV_HTML: &str = "<p class=nav><a href=/inbox>&larr; Inbox</a></p>";

/// Escape text for safe HTML body content.
#[must_use]
pub fn html_escape(raw: &str) -> String {
    raw.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

/// Escape text for safe HTML attribute content.
#[must_use]
pub fn html_attr(raw: &str) -> String {
    raw.replace('&', "&amp;")
        .replace('"', "&quot;")
        .replace('<', "&lt;")
}

/// Render an age string (e.g. "5s", "12m", "3h", "2d") from a duration in ms.
#[must_use]
pub fn format_age(ms: u64) -> String {
    let secs = ms / 1000;
    if secs < 60 {
        format!("{secs}s")
    } else if secs < 3_600 {
        format!("{}m", secs / 60)
    } else if secs < 86_400 {
        format!("{}h", secs / 3_600)
    } else {
        format!("{}d", secs / 86_400)
    }
}

/// Difference between `now_ms` and `past_ms`, clamped to 0.
#[must_use]
pub fn unix_now_ms_diff(past_ms: u64) -> u64 {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.as_millis() as u64);
    now.saturating_sub(past_ms)
}

/// Truncate a string to `max_chars`, appending an ellipsis if cut.
#[must_use]
pub fn truncate(s: &str, max_chars: usize) -> String {
    if s.chars().count() <= max_chars {
        return s.to_string();
    }
    let mut out: String = s.chars().take(max_chars.saturating_sub(1)).collect();
    out.push('…');
    out
}

/// Map `Urgency` to its CSS class for card styling.
#[must_use]
pub fn urgency_class(u: crate::spec::Urgency) -> &'static str {
    use crate::spec::Urgency::{Info, Warning, Error, Secret};
    match u {
        Info => "info",
        Warning => "warn",
        Error => "urgent",
        Secret => "info",
    }
}

/// Map `Urgency` to a short human label.
#[must_use]
pub fn urgency_label(u: crate::spec::Urgency) -> &'static str {
    use crate::spec::Urgency::{Info, Warning, Error, Secret};
    match u {
        Info => "Info",
        Warning => "Warning",
        Error => "Error",
        Secret => "Secret",
    }
}

/// Map `FieldSpec` to a short kind label (e.g. "text", "yes / no").
#[must_use]
pub fn field_kind_label(f: &FieldSpec) -> &'static str {
    match f {
        FieldSpec::Text { .. } => "text",
        FieldSpec::LongText { .. } => "long text",
        FieldSpec::Integer { .. } => "integer",
        FieldSpec::Choice { .. } => "choice",
        FieldSpec::Boolean { .. } => "yes / no",
        FieldSpec::DateTime { .. } => "date",
    }
}
