//! Render dispatcher — chooses the right platform renderer.

use crate::error::ElicitError;
use crate::options::ElicitOptions;
use crate::platform;
use crate::spec::ElicitResponse;
use crate::spec::PromptSpec;
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

    // The TUI renderer uses a sentinel error string for user cancellation;
    // translate it to a proper Cancelled response.
    let result = result.map_err(|e| match e {
        ElicitError::InvalidSpec(msg) if msg == platform::tty::CANCELLED_SENTINEL => {
            ElicitError::InvalidSpec(platform::tty::CANCELLED_SENTINEL.into())
        }
        other => other,
    });

    let final_response = match result {
        Ok(response) => response,
        Err(ElicitError::InvalidSpec(msg)) if msg == platform::tty::CANCELLED_SENTINEL => {
            ElicitResponse::Cancelled { notes: None }
        }
        Err(e) => return Err(e),
    };

    tracing_setup::trace_request_end(&request_id, &final_response);

    Ok(final_response)
}