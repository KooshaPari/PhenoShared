//! Render dispatcher — chooses the right platform renderer.

use crate::error::ElicitError;
use crate::options::ElicitOptions;
use crate::platform;
use crate::spec::{self, ElicitResponse, FieldValue, PromptSpec};
use crate::tracing_setup;

/// Render a popup and return the response. This is the synchronous
/// internal entry point.
pub fn dispatch(spec: &PromptSpec, opts: &ElicitOptions) -> Result<ElicitResponse, ElicitError> {
    spec.validate().map_err(ElicitError::InvalidSpec)?;

    let request_id = spec
        .request_id
        .clone()
        .unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

    tracing_setup::trace_request_start(&request_id, spec);

    let result = platform::render_on_platform(spec, opts);

    let final_response = match result {
        Ok(response) => response,
        // The TTY renderer signals user cancellation with a sentinel error
        // string; translate it into a typed Cancelled response.
        Err(ElicitError::InvalidSpec(msg)) if msg == platform::tty::CANCELLED_SENTINEL => {
            ElicitResponse::Cancelled { notes: None }
        }
        // A backend-side timeout is a legitimate outcome, not a failure.
        Err(ElicitError::Timeout(elapsed)) => ElicitResponse::TimedOut {
            elapsed_secs: elapsed.as_secs_f64(),
        },
        Err(e) => return Err(e),
    };

    // Every backend returns a raw *string*; the spec declares the intended
    // kind. Coerce once here so all platforms (macOS/windows/linux/tty)
    // hand the caller the typed FieldValue it asked for. Doing this per
    // backend previously left `Text` leaking out of the untested ones.
    let final_response = match final_response {
        ElicitResponse::Answered { value: FieldValue::Text(raw), notes } => {
            ElicitResponse::Answered {
                value: spec::coerce(&spec.field, &raw)?,
                notes,
            }
        }
        other => other,
    };

    tracing_setup::trace_request_end(&request_id, &final_response);

    Ok(final_response)
}