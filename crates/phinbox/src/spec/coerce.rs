//! Coerce a renderer's raw string answer into the typed [`FieldValue`]
//! the caller asked for.
//!
//! Every GUI/terminal backend ultimately hands back a *string*: AppleScript's
//! `display dialog` returns text, zenity prints text, PowerShell prints text,
//! inquire returns Rust values that we already stringify. The `FieldSpec`,
//! however, declares the *intended* kind (Boolean, Integer, Choice, ...).
//!
//! Without this step the caller receives `FieldValue::Text("OK")` for a
//! Boolean prompt and rejects it as an unexpected variant. Coercion happens
//! once, centrally, in [`crate::render::dispatch`], so it applies uniformly
//! to every platform backend.

use crate::error::ElicitError;
use crate::spec::{DateTimeKind, FieldSpec, FieldValue};

/// Parse `raw` into the value kind declared by `spec`.
///
/// # Errors
///
/// Returns [`ElicitError::RendererFailed`] when `raw` cannot be interpreted
/// as the requested kind (non-integer text for an Integer field, an unknown
/// label for a Choice, an unparseable date, ...).
pub fn coerce(spec: &FieldSpec, raw: &str) -> Result<FieldValue, ElicitError> {
    match spec {
        FieldSpec::Text { .. } => Ok(FieldValue::Text(raw.to_string())),
        FieldSpec::LongText { .. } => Ok(FieldValue::LongText(raw.to_string())),
        FieldSpec::Integer { min, max, .. } => {
            // Some backends append units or whitespace; trim before parsing.
            let v: i64 = raw.trim().parse().map_err(|_| {
                ElicitError::RendererFailed(format!("not an integer: {raw:?}"))
            })?;
            if let Some(min) = min {
                if v < *min {
                    return Err(ElicitError::RendererFailed(format!(
                        "value {v} < min {min}"
                    )));
                }
            }
            if let Some(max) = max {
                if v > *max {
                    return Err(ElicitError::RendererFailed(format!(
                        "value {v} > max {max}"
                    )));
                }
            }
            Ok(FieldValue::Integer(v))
        }
        FieldSpec::Choice { options, .. } => {
            let needle = raw.trim();
            for (i, o) in options.iter().enumerate() {
                if o.label.eq_ignore_ascii_case(needle) || o.value.eq_ignore_ascii_case(needle) {
                    return Ok(FieldValue::Choice {
                        value: o.value.clone(),
                        index: i,
                    });
                }
            }
            Err(ElicitError::RendererFailed(format!(
                "value {raw:?} not in choice options"
            )))
        }
        FieldSpec::Boolean { .. } => match raw.trim().to_ascii_lowercase().as_str() {
            "yes" | "true" | "ok" | "1" | "on" => Ok(FieldValue::Boolean(true)),
            "no" | "false" | "cancel" | "0" | "off" => Ok(FieldValue::Boolean(false)),
            other => Err(ElicitError::RendererFailed(format!(
                "not a boolean: {other:?}"
            ))),
        },
        FieldSpec::DateTime { picker_kind, .. } => {
            let s = raw.trim().to_string();
            let bad = |expected: &str| {
                ElicitError::RendererFailed(format!("expected {expected}, got {s:?}"))
            };
            match picker_kind {
                DateTimeKind::Date => {
                    if chrono::NaiveDate::parse_from_str(&s, "%Y-%m-%d").is_err() {
                        return Err(bad("a date (YYYY-MM-DD)"));
                    }
                }
                DateTimeKind::Time => {
                    if chrono::NaiveTime::parse_from_str(&s, "%H:%M").is_err() {
                        return Err(bad("a time (HH:MM)"));
                    }
                }
                DateTimeKind::DateTime => {
                    if chrono::DateTime::parse_from_rfc3339(&s).is_err() {
                        return Err(bad("an RFC3339 timestamp"));
                    }
                }
            }
            Ok(FieldValue::DateTime(s))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::spec::ChoiceOption;

    fn integer(min: Option<i64>, max: Option<i64>) -> FieldSpec {
        FieldSpec::Integer {
            label: "n".into(),
            min,
            max,
            default: None,
        }
    }

    #[test]
    fn coerces_boolean_from_button_labels() {
        let spec = FieldSpec::Boolean {
            label: "?".into(),
            default: None,
        };
        assert!(matches!(coerce(&spec, "OK").unwrap(), FieldValue::Boolean(true)));
        assert!(matches!(coerce(&spec, "Cancel").unwrap(), FieldValue::Boolean(false)));
        assert!(coerce(&spec, "maybe").is_err());
    }

    #[test]
    fn coerces_choice_by_label_or_value() {
        let spec = FieldSpec::Choice {
            label: "t".into(),
            options: vec![
                ChoiceOption {
                    value: "staging".into(),
                    label: "Staging".into(),
                    description: None,
                },
                ChoiceOption {
                    value: "prod".into(),
                    label: "Production".into(),
                    description: None,
                },
            ],
            default_index: None,
        };
        // kdialog prints the *value*; zenity prints the *label*.
        assert!(matches!(
            coerce(&spec, "staging").unwrap(),
            FieldValue::Choice { index: 0, .. }
        ));
        assert!(matches!(
            coerce(&spec, "Production").unwrap(),
            FieldValue::Choice { index: 1, .. }
        ));
        assert!(coerce(&spec, "nope").is_err());
    }

    #[test]
    fn coerces_integer_and_enforces_bounds() {
        assert!(matches!(
            coerce(&integer(Some(0), Some(10)), "5").unwrap(),
            FieldValue::Integer(5)
        ));
        assert!(coerce(&integer(Some(0), Some(10)), "11").is_err());
        assert!(coerce(&integer(None, None), "abc").is_err());
    }

    #[test]
    fn coerces_date_without_panicking_on_short_input() {
        // Regression guard: short input must be an Err, never a panic.
        // (`&raw[..10]` used to panic on inputs shorter than 10 bytes.)
        let spec = FieldSpec::DateTime {
            label: "d".into(),
            default: None,
            picker_kind: DateTimeKind::Date,
        };
        for raw in ["", "x", "2026", "not-a-date", "2026-13-45", "2026-02-30"] {
            assert!(coerce(&spec, raw).is_err(), "expected Err for {raw:?}");
        }
        // chrono accepts unpadded components; that is a valid date, not an error.
        assert!(coerce(&spec, "2026-09-18").is_ok());
        assert!(coerce(&spec, " 2026-09-18 ").is_ok());
    }

    #[test]
    fn coerces_time_and_datetime() {
        let t = FieldSpec::DateTime {
            label: "t".into(),
            default: None,
            picker_kind: DateTimeKind::Time,
        };
        assert!(coerce(&t, "14:30").is_ok());
        assert!(coerce(&t, "25:99").is_err());

        let dt = FieldSpec::DateTime {
            label: "dt".into(),
            default: None,
            picker_kind: DateTimeKind::DateTime,
        };
        assert!(coerce(&dt, "2026-09-18T14:30:00Z").is_ok());
        assert!(coerce(&dt, "2026-09-18").is_err());
    }

    #[test]
    fn text_kinds_pass_through_unchanged() {
        let text = FieldSpec::Text {
            label: "t".into(),
            default: None,
            placeholder: None,
            max_length: None,
            secret: false,
            pattern: None,
        };
        assert!(matches!(
            coerce(&text, "anything at all").unwrap(),
            FieldValue::Text(ref s) if s == "anything at all"
        ));
    }
}
