//! phinbox — native OS popup elicitation for autonomous agents.
//!
//! This crate exposes three coordinated surfaces:
//!
//! - **Library** ([`elicit`], [`elicit_async`], [`ElicitOptions`]) for use
//!   from Rust code.
//! - **CLI binary** (`phinbox`) for shell scripting.
//! - **MCP server** (`phinbox-mcp`) for use as an MCP tool from Forge,
//!   Codex, Cursor, or any stdio JSON-RPC client.
//!
//! The popup is rendered by the operating system — `NSAlert` on macOS, a
//! Win32 form on Windows, and a zenity/kdialog/Tk/inquire chain on Linux.
//! The same [`PromptSpec`] / [`ElicitResponse`] types flow through every
//! surface; the host agent never sees the platform split.
//!
//! See `docs/RESEARCH.md` for the full design rationale and
//! `plans/2026-07-21-phinbox-EXECUTION-PLAN-v1.md` for the phased
//! implementation plan.

pub mod spec;
pub mod options;
pub mod error;
pub mod escape;
pub mod platform;
pub mod render;
pub mod schema;
pub mod tracing_setup;
pub mod inbox;
pub mod installer;
pub mod views;

#[cfg(feature = "mcp")]
pub mod mcp;

#[cfg(feature = "observability")]
pub mod metrics;

/// OS tray icon (status bar item / notification area / libappindicator).
///
/// Always available — when `tray-native` is disabled (the default) the
/// module exposes a `NoopTray` so the daemon doesn't need conditional
/// compilation at every call site.
pub mod tray;

/// Terminal-UI inbox viewer (`phinbox inbox --tui`).
///
/// Renders a split-pane terminal interface over the same on-disk inbox the
/// daemon writes to. Uses `ratatui` + `crossterm`; falls back to plain-text
/// rendering when no TTY is available (e.g. CI, `TERM=dumb`, ssh without
/// TTY allocation).
pub mod tui;

pub use error::ElicitError;
pub use inbox::daemon::{
    live_url as inbox_live_url, read_lockfile as inbox_read_lockfile, DEFAULT_PORT as INBOX_DEFAULT_PORT,
};
pub use inbox::notify::{inbox_open_url, inbox_open_url_for, open_in_default_browser, NotifyAttempt, NotifyChannels};
pub use inbox::{
    load as inbox_load, list_pending as inbox_list_pending, wait_for_response, PendingRequest,
    RequestOrigin, RequestState,
};
pub use options::{ElicitOptions, RendererPreference};
pub use platform::Platform;
pub use spec::{
    ButtonSpec, ChoiceOption, DateTimeKind, ElicitResponse, FieldSpec, FieldValue, NotesSpec,
    PromptSpec, Urgency,
};
pub use tui::{
    render_plain as tui_render_plain, run as tui_run, snapshot_inbox as tui_snapshot, ListEntry,
    TuiOutcome, ViewerState,
};
pub use tray::{build_tray, MenuAction, Tray, TrayConfig, TrayError, TrayEvent, TrayResult};
pub use views::{render_form_html, render_full_html, render_plain_text, render_summary};

/// Render a popup and block until the user responds (or the popup times out).
///
/// This is the synchronous entry point. For async callers, see [`elicit_async`].
///
/// # Errors
///
/// Returns [`ElicitError::InvalidSpec`] if [`PromptSpec`] validation fails,
/// [`ElicitError::NoRenderer`] if no GUI is available and the TUI fallback
/// is also unavailable, [`ElicitError::RendererFailed`] if the OS renderer
/// crashed, or [`ElicitError::Io`] / [`ElicitError::Json`] for I/O and
/// parsing failures respectively.
///
/// The user clicking **Cancel** is **not** an error — it's surfaced as
/// [`ElicitResponse::Cancelled`]. The popup timing out is also not an
/// error — it's [`ElicitResponse::TimedOut`].
pub fn elicit(spec: &PromptSpec) -> Result<ElicitResponse, ElicitError> {
    elicit_with(spec, &ElicitOptions::default())
}

/// Render a popup with explicit options.
///
/// See [`ElicitOptions`] for the override knobs.
pub fn elicit_with(
    spec: &PromptSpec,
    opts: &ElicitOptions,
) -> Result<ElicitResponse, ElicitError> {
    render::dispatch(spec, opts)
}

/// Async wrapper around [`elicit`].
///
/// Uses `tokio::task::spawn_blocking` so the runtime isn't blocked while
/// the popup is open. The returned future resolves with the same
/// [`ElicitResponse`] (or [`ElicitError`]) the sync version would return.
///
/// # Errors
///
/// Same as [`elicit`], plus a join error from the blocking task if the
/// runtime shuts down mid-popup.
pub async fn elicit_async(spec: PromptSpec) -> Result<ElicitResponse, ElicitError> {
    tokio::task::spawn_blocking(move || elicit(&spec))
        .await
        .map_err(|e| ElicitError::RendererFailed(format!("join: {e}")))?
}

/// Return the JSON Schema for [`PromptSpec`] as a [`serde_json::Value`].
///
/// The MCP server uses this to populate `inputSchema` in `tools/list`,
/// and the CLI uses it for `phinbox schema`.
#[must_use]
pub fn schema_json() -> serde_json::Value {
    schema::prompt_spec_schema()
}

/// Return the JSON Schema for [`ElicitResponse`] as a [`serde_json::Value`].
///
/// Used by the MCP server for `outputSchema` and by the CLI for
/// `phinbox schema --response`.
#[must_use]
pub fn schema_response_json() -> serde_json::Value {
    schema::elicit_response_schema()
}

/// Identify the running platform (compile-time + runtime tweak).
#[must_use]
pub fn platform() -> Platform {
    platform::detect()
}

/// Detect which renderer would be used right now for the given preference.
///
/// Useful for the CLI's `phinbox detect` subcommand and for the agent's
/// pre-flight check ("should I use this tool or fall back to inline
/// questions?").
#[must_use]
pub fn detect_renderer(pref: RendererPreference) -> platform::RendererKind {
    platform::detect_renderer(pref)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn platform_does_not_panic() {
        let _ = platform();
    }

    #[test]
    fn detect_renderer_does_not_panic() {
        let _ = detect_renderer(RendererPreference::AutoGui);
        let _ = detect_renderer(RendererPreference::ForceTty);
        let _ = detect_renderer(RendererPreference::ForceGui);
    }

    #[test]
    fn schema_json_is_valid_json_object() {
        let s = schema_json();
        assert!(s.is_object(), "schema_json() must return a JSON object");
        assert!(
            s.get("$defs").is_some() || s.get("definitions").is_some(),
            "schema must contain $defs or definitions"
        );
    }
}
