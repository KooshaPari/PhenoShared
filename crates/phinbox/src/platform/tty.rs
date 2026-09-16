//! Terminal-based fallback renderer using the [`inquire`] crate.
//!
//! This is used when no GUI is available (CI, SSH without X forwarding,
//! `--renderer=force-tty`).

use inquire::error::InquireError;

use crate::error::ElicitError;
use crate::options::ElicitOptions;
use crate::spec::{
    DateTimeKind, ElicitResponse, FieldSpec, FieldValue, NotesSpec, PromptSpec, Urgency,
};

/// Render a prompt via the terminal.
///
/// # Errors
///
/// Returns [`ElicitError::RendererFailed`] if an inquire prompt fails for
/// any reason other than user cancellation. User cancellation is returned
/// as [`ElicitResponse::Cancelled`].
pub fn render(spec: &PromptSpec, _opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError> {
    let value = match &spec.field {
        FieldSpec::Text {
            label,
            default,
            placeholder,
            max_length,
            secret: _,
            pattern,
        } => {
            let v = inquire::Text::new(label)
                .with_help_message(spec.question.as_str())
                .with_initial_value(default.as_deref().unwrap_or(""))
                .with_placeholder(placeholder.as_deref().unwrap_or(""))
                .prompt()
                .map_err(map_inquire_error)?;
            if let Some(max) = max_length {
                if v.chars().count() > *max as usize {
                    return Err(ElicitError::InvalidSpec(format!(
                        "value exceeds max_length {max}"
                    )));
                }
            }
            if let Some(re) = pattern {
                let regex = regex::Regex::new(re)
                    .map_err(|e| ElicitError::InvalidSpec(format!("invalid pattern: {e}")))?;
                if !regex.is_match(&v) {
                    return Err(ElicitError::RendererFailed(format!(
                        "value does not match pattern {re}"
                    )));
                }
            }
            FieldValue::Text(v)
        }

        FieldSpec::LongText {
            label,
            default,
            max_length,
        } => {
            // inquire::Editor is for single-line; for multi-line we use
            // Text with a help message hinting at multi-line entry. This
            // is a deliberate trade-off — we don't want to launch a blocking
            // editor in a TTY fallback context.
            let v = inquire::Text::new(label)
                .with_help_message("(end with a single blank line to finish)")
                .with_initial_value(default.as_deref().unwrap_or(""))
                .prompt()
                .map_err(map_inquire_error)?;
            if let Some(max) = max_length {
                if v.chars().count() > *max as usize {
                    return Err(ElicitError::InvalidSpec(format!(
                        "value exceeds max_length {max}"
                    )));
                }
            }
            FieldValue::LongText(v)
        }

        FieldSpec::Integer {
            label,
            min,
            max,
            default,
        } => {
            let starting = default.map(|d| d.to_string());
            let mut p = inquire::CustomType::<i64>::new(label)
                .with_help_message(spec.question.as_str())
                .with_error_message("Please enter a valid integer");
            if let Some(s) = starting.as_deref() {
                p = p.with_starting_input(s);
            }
            let value = p.prompt().map_err(map_inquire_error)?;
            if let Some(min) = min {
                if value < *min {
                    return Err(ElicitError::InvalidSpec(format!(
                        "value {value} < min {min}"
                    )));
                }
            }
            if let Some(max) = max {
                if value > *max {
                    return Err(ElicitError::InvalidSpec(format!(
                        "value {value} > max {max}"
                    )));
                }
            }
            FieldValue::Integer(value)
        }

        FieldSpec::Choice {
            label,
            options,
            default_index,
        } => {
            if options.is_empty() {
                return Err(ElicitError::InvalidSpec(
                    "choice field has zero options".into(),
                ));
            }
            // inquire::Select returns the selected value (T), not an index.
            // We match the returned label back to the option to recover the
            // canonical value + index.
            let labels: Vec<String> = options
                .iter()
                .map(|o| match &o.description {
                    Some(d) => format!("{} — {d}", o.label),
                    None => o.label.clone(),
                })
                .collect();
            let mut p =
                inquire::Select::new(label, labels).with_help_message(spec.question.as_str());
            if let Some(idx) = default_index {
                p = p.with_starting_cursor(*idx);
            }
            let selected = p.prompt().map_err(map_inquire_error)?;
            // Find the matching option. The displayed label is either the
            // raw label or "{label} — {description}"; match on either.
            let (chosen_index, chosen_value) = options
                .iter()
                .enumerate()
                .find_map(|(i, o)| {
                    let displayed = match &o.description {
                        Some(d) => format!("{} — {d}", o.label),
                        None => o.label.clone(),
                    };
                    if displayed == selected || o.label == selected {
                        Some((i, o.value.clone()))
                    } else {
                        None
                    }
                })
                .ok_or_else(|| {
                    ElicitError::RendererFailed(format!(
                        "selected label {selected:?} did not match any option"
                    ))
                })?;
            FieldValue::Choice {
                value: chosen_value,
                index: chosen_index,
            }
        }

        FieldSpec::Boolean { label, default } => {
            let value = inquire::Confirm::new(label)
                .with_help_message(spec.question.as_str())
                .with_default(default.unwrap_or(false))
                .prompt()
                .map_err(map_inquire_error)?;
            FieldValue::Boolean(value)
        }

        FieldSpec::DateTime {
            label,
            default,
            picker_kind,
        } => match picker_kind {
            DateTimeKind::Date => {
                let mut p = inquire::DateSelect::new(label)
                    .with_help_message(spec.question.as_str());
                if let Some(d) = default {
                    // RFC3339 date prefix
                    if let Ok(parsed) = chrono::NaiveDate::parse_from_str(&d[..10], "%Y-%m-%d") {
                        p = p.with_starting_date(parsed);
                    }
                }
                let v = p
                    .prompt()
                    .map_err(map_inquire_error)?
                    .format("%Y-%m-%d")
                    .to_string();
                FieldValue::DateTime(v)
            }
            DateTimeKind::Time => {
                // inquire 0.7 has no TimeSelect; accept HH:MM via Text and validate.
                let v = inquire::Text::new(label)
                    .with_help_message("Format: HH:MM (24-hour)")
                    .with_initial_value(default.as_deref().unwrap_or(""))
                    .prompt()
                    .map_err(map_inquire_error)?;
                // Validate HH:MM
                if chrono::NaiveTime::parse_from_str(&v, "%H:%M").is_err() {
                    return Err(ElicitError::RendererFailed(
                        "expected time in HH:MM format".into(),
                    ));
                }
                FieldValue::DateTime(v)
            }
            DateTimeKind::DateTime => {
                // inquire 0.7 has no DateTimeSelect; combine Date + Time.
                let date = inquire::DateSelect::new(label)
                    .with_help_message(spec.question.as_str())
                    .prompt()
                    .map_err(map_inquire_error)?;
                let time_str = inquire::Text::new("Time (HH:MM, 24-hour)")
                    .with_initial_value("00:00")
                    .prompt()
                    .map_err(map_inquire_error)?;
                let t = chrono::NaiveTime::parse_from_str(&time_str, "%H:%M").map_err(|e| {
                    ElicitError::RendererFailed(format!("invalid time: {e}"))
                })?;
                let dt = date.and_time(t);
                FieldValue::DateTime(dt.and_utc().to_rfc3339())
            }
        },
    };

    // Optional notes box
    let notes = match &spec.notes {
        Some(notes_spec) => prompt_notes(notes_spec, &spec.question)?,
        None => None,
    };

    // Warn loudly if urgency is Secret but the user has no GUI — secrets in
    // terminal buffers are a known footgun.
    if matches!(spec.urgency, Urgency::Secret) {
        eprintln!(
            "warning: urgency=secret over TTY; the entered value will be visible in your shell scrollback."
        );
    }

    Ok(ElicitResponse::Answered { value, notes })
}

fn prompt_notes(spec: &NotesSpec, _context: &str) -> Result<Option<String>, ElicitError> {
    let result: Option<String> = if spec.required {
        let v = inquire::Text::new(&spec.label)
            .with_help_message("(required)")
            .prompt()
            .map_err(map_inquire_error)?;
        Some(v)
    } else {
        inquire::Text::new(&spec.label)
            .with_help_message("(optional)")
            .prompt()
            .ok()
    };

    if let Some(ref s) = result {
        if let Some(max) = spec.max_length {
            if s.chars().count() > max as usize {
                return Err(ElicitError::InvalidSpec(format!(
                    "notes exceed max_length {max}"
                )));
            }
        }
    }
    Ok(result.filter(|s| !s.is_empty()))
}

/// Map an inquire error to our error type. Cancellation is mapped to a
/// sentinel error; the dispatcher in `render::dispatch` recognizes it
/// and converts it into `ElicitResponse::Cancelled`.
pub(crate) fn map_inquire_error(e: InquireError) -> ElicitError {
    match e {
        InquireError::OperationCanceled
        | InquireError::OperationInterrupted
        | InquireError::NotTTY => ElicitError::InvalidSpec(CANCELLED_SENTINEL.into()),
        // inquire returns a generic IO error if it can't init the reader
        // (e.g., stdin is closed in a child process). For the purposes of
        // this library, that's also a "no response" condition — treat it
        // as cancellation so callers see a typed Cancelled response
        // instead of an opaque IO failure.
        InquireError::IO(_) => ElicitError::InvalidSpec(CANCELLED_SENTINEL.into()),
        other => ElicitError::RendererFailed(format!("inquire: {other}")),
    }
}

/// Sentinel used by the TUI renderer to signal user cancellation.
pub(crate) const CANCELLED_SENTINEL: &str = "__user_cancelled__";
