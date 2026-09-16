use std::time::Duration;

use crate::error::ElicitError;
use crate::spec::{DateTimeKind, ElicitResponse, FieldSpec, FieldValue};

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
            let value = FieldValue::Text(entered.to_string());
            Ok(ElicitResponse::Answered {
                value,
                notes: notes_raw.filter(|s| !s.is_empty()),
            })
        }
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

/// Parse the user's raw text into the correct `FieldValue` variant.
///
/// The macOS renderer returns a `FieldValue::Text` for every input kind
/// (because `display dialog` doesn't preserve types). The dispatcher uses
/// this helper to coerce the string into the requested `FieldSpec` kind.
#[allow(dead_code)]
pub fn coerce_value(spec: &FieldSpec, raw: &str) -> Result<FieldValue, ElicitError> {
    match spec {
        FieldSpec::Text { .. } => Ok(FieldValue::Text(raw.to_string())),
        FieldSpec::LongText { .. } => Ok(FieldValue::LongText(raw.to_string())),
        FieldSpec::Integer { min, max, .. } => {
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
        }
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
                }
                DateTimeKind::Time => {
                    if s.len() != 5 {
                        return Err(ElicitError::RendererFailed(format!(
                            "time must be HH:MM, got {s:?}"
                        )));
                    }
                }
                DateTimeKind::DateTime => {}
            }
            Ok(FieldValue::DateTime(s))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::spec::{FieldSpec, FieldValue};

    #[test]
    fn coerce_value_integer() {
        let spec = FieldSpec::Integer {
            label: "n".into(),
            min: Some(0),
            max: Some(10),
            default: None,
        };
        let v = coerce_value(&spec, "5").unwrap();
        assert!(matches!(v, FieldValue::Integer(5)));
    }

    #[test]
    fn coerce_value_boolean() {
        let spec = FieldSpec::Boolean {
            label: "?".into(),
            default: None,
        };
        assert!(matches!(
            coerce_value(&spec, "yes").unwrap(),
            FieldValue::Boolean(true)
        ));
        assert!(matches!(
            coerce_value(&spec, "no").unwrap(),
            FieldValue::Boolean(false)
        ));
    }

    #[test]
    fn parse_output_answered() {
        let r = parse_output(b"answered|OK|hello|", b"", Duration::from_secs(1)).unwrap();
        assert!(r.is_answered());
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
