use std::time::Duration;

use crate::{
    error::ElicitError,
    spec::{DateTimeKind, ElicitResponse, FieldSpec, FieldValue},
};

/// Parse `osascript`'s stdout/stderr into an [`ElicitResponse`].
pub(super) fn parse_output(
    stdout: &[u8],
    stderr: &[u8],
    elapsed: Duration,
) -> Result<ElicitResponse, ElicitError> {
    let text = std::str::from_utf8(stdout)
        .map_err(|e| ElicitError::RendererFailed(format!("non-utf8 stdout: {e}")))?
        .trim();

    if text.is_empty() {
        let err = std::str::from_utf8(stderr).unwrap_or("(non-utf8 stderr)");
        return Ok(ElicitResponse::Failed {
            reason: format!("osascript produced no stdout; stderr: {err}"),
        });
    }

    let parts: Vec<&str> = text.splitn(4, '|').collect();
    if parts.len() < 3 {
        return Ok(ElicitResponse::Failed {
            reason: format!("unexpected osascript output: {text:?}"),
        });
    }

    let status = parts[0];
    let entered = parts[2];
    let notes_raw = parts.get(3).map(|s| (*s).to_string());

    match status {
        "answered" => {
            // Button-only dialogs (Boolean/Choice — no `default answer` box)
            // carry the semantic answer in the button label, not the text.
            // Fall back to it so the render-boundary coercion sees "OK",
            // "Approve", etc. rather than an empty string.
            let raw = if entered.is_empty() {
                parts[1]
            } else {
                entered
            };
            let value = FieldValue::Text(raw.to_string());
            Ok(ElicitResponse::Answered {
                value,
                notes: notes_raw.filter(|s| !s.is_empty()),
            })
        },
        "cancelled" => Ok(ElicitResponse::Cancelled {
            notes: notes_raw.filter(|s| !s.is_empty()),
        }),
        "timed_out" => Ok(ElicitResponse::TimedOut {
            elapsed_secs: elapsed.as_secs_f64(),
        }),
        "failed" => Ok(ElicitResponse::Failed {
            reason: entered.to_string(),
        }),
        other => Ok(ElicitResponse::Failed {
            reason: format!("unknown status '{other}' in osascript output"),
        }),
    }
}

/// Coerce the macOS renderer's raw text into the `FieldSpec`'s kind.
///
/// The macOS renderer returns `FieldValue::Text` for every input kind, because
/// `display dialog` does not preserve types. Callers use this helper so a
/// `FieldSpec::Integer` never comes back as `Text("5")`.
///
/// Ported from the `absorb-phenoUtils` branch (commit 497e893f), which was never
/// merged into this tree; without it callers had to coerce inline and drifted.
///
/// `dead_code` is expected until the elicitation callers switch to it: the
/// branch's refactor touched more files than this one. Tests pin the behaviour
/// so that adoption is safe.
#[allow(dead_code)]
pub fn coerce_value(spec: &FieldSpec, raw: &str) -> Result<FieldValue, ElicitError> {
    match spec {
        FieldSpec::Text { .. } => Ok(FieldValue::Text(raw.to_string())),
        FieldSpec::LongText { .. } => Ok(FieldValue::LongText(raw.to_string())),
        FieldSpec::Integer { min, max, .. } => {
            let v: i64 = raw
                .trim()
                .parse()
                .map_err(|_| ElicitError::RendererFailed(format!("not an integer: {raw:?}")))?;
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
        },
        FieldSpec::Choice { options, .. } => {
            let lower = raw.to_lowercase();
            for (i, o) in options.iter().enumerate() {
                if o.label.to_lowercase() == lower || o.value.to_lowercase() == lower {
                    return Ok(FieldValue::Choice {
                        value: o.value.clone(),
                        index: i,
                    });
                }
            }
            Err(ElicitError::RendererFailed(format!(
                "value {raw:?} not in choice options"
            )))
        },
        FieldSpec::Boolean { .. } => match raw.to_lowercase().as_str() {
            "yes" | "true" | "ok" | "1" => Ok(FieldValue::Boolean(true)),
            "no" | "false" | "cancel" | "0" => Ok(FieldValue::Boolean(false)),
            _ => Err(ElicitError::RendererFailed(format!(
                "not a boolean: {raw:?}"
            ))),
        },
        FieldSpec::DateTime { picker_kind, .. } => {
            let s = raw.to_string();
            match picker_kind {
                DateTimeKind::Date => {
                    if s.len() != 10 {
                        return Err(ElicitError::RendererFailed(format!(
                            "date must be YYYY-MM-DD, got {s:?}"
                        )));
                    }
                },
                DateTimeKind::Time => {
                    if s.len() != 5 {
                        return Err(ElicitError::RendererFailed(format!(
                            "time must be HH:MM, got {s:?}"
                        )));
                    }
                },
                DateTimeKind::DateTime => {},
            }
            Ok(FieldValue::DateTime(s))
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_output_answered() {
        let r = parse_output(b"answered|OK|hello|", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_answered());
    }

    #[test]
    fn parse_output_answered_button_only_uses_button_label() {
        // Button-only dialog: empty text, answer lives in the button label.
        let r = parse_output(b"answered|Approve||", b"", Duration::from_secs(1)).unwrap();
        match r {
            crate::spec::ElicitResponse::Answered { value, .. } => {
                assert!(matches!(value, crate::spec::FieldValue::Text(ref t) if t == "Approve"));
            },
            other => panic!("expected Answered, got {other:?}"),
        }
    }

    #[test]
    fn parse_output_answered_empty_text_and_empty_button() {
        // Degenerate: both empty — must not panic; yields Text("").
        let r = parse_output(b"answered|||", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_answered());
    }

    fn spec_integer() -> FieldSpec {
        FieldSpec::Integer {
            label: "n".into(),
            min: Some(0),
            max: Some(10),
            default: None,
        }
    }

    #[test]
    fn coerce_value_integer_parses_and_accepts_in_range() {
        match coerce_value(&spec_integer(), " 5 ").unwrap() {
            FieldValue::Integer(v) => assert_eq!(v, 5),
            other => panic!("expected Integer, got {other:?}"),
        }
    }

    #[test]
    fn coerce_value_integer_rejects_out_of_range() {
        assert!(coerce_value(&spec_integer(), "11").is_err());
        assert!(coerce_value(&spec_integer(), "-1").is_err());
    }

    #[test]
    fn coerce_value_integer_rejects_non_numeric() {
        // The whole point of the helper: a text answer must not silently pass.
        assert!(coerce_value(&spec_integer(), "five").is_err());
    }

    #[test]
    fn coerce_value_boolean_accepts_yes_no() {
        let spec = FieldSpec::Boolean {
            label: "b".into(),
            default: None,
        };
        assert!(matches!(
            coerce_value(&spec, "YES").unwrap(),
            FieldValue::Boolean(true)
        ));
        assert!(matches!(
            coerce_value(&spec, "no").unwrap(),
            FieldValue::Boolean(false)
        ));
        assert!(coerce_value(&spec, "maybe").is_err());
    }

    #[test]
    fn coerce_value_choice_matches_label_or_value() {
        let spec = FieldSpec::Choice {
            label: "c".into(),
            options: vec![
                crate::spec::ChoiceOption {
                    value: "rs".into(),
                    label: "Rust".into(),
                    description: None,
                },
                crate::spec::ChoiceOption {
                    value: "py".into(),
                    label: "Python".into(),
                    description: None,
                },
            ],
            default_index: None,
        };
        match coerce_value(&spec, "python").unwrap() {
            FieldValue::Choice { value, index } => {
                assert_eq!(value, "py");
                assert_eq!(index, 1);
            },
            other => panic!("expected Choice, got {other:?}"),
        }
        assert!(coerce_value(&spec, "cobol").is_err());
    }

    #[test]
    fn coerce_value_datetime_enforces_shape() {
        let spec = FieldSpec::DateTime {
            label: "d".into(),
            default: None,
            picker_kind: DateTimeKind::Date,
        };
        assert!(matches!(
            coerce_value(&spec, "2026-11-06").unwrap(),
            FieldValue::DateTime(_)
        ));
        assert!(coerce_value(&spec, "2026-11-06T10:00:00Z").is_err());
    }

    #[test]
    fn parse_output_cancelled() {
        let r = parse_output(b"cancelled|Cancel|||", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_cancelled());
    }

    #[test]
    fn parse_output_failed() {
        let r = parse_output(b"failed|Error|something bad|", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_failed());
    }
}
