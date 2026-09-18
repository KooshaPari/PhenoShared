use std::time::Duration;

use crate::error::ElicitError;
use crate::spec::{ElicitResponse, FieldValue};

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
            let raw = if entered.is_empty() { parts[1] } else { entered };
            let value = FieldValue::Text(raw.to_string());
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
            }
            other => panic!("expected Answered, got {other:?}"),
        }
    }

    #[test]
    fn parse_output_answered_empty_text_and_empty_button() {
        // Degenerate: both empty — must not panic; yields Text("").
        let r = parse_output(b"answered|||", b"", Duration::from_secs(1)).unwrap();
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
