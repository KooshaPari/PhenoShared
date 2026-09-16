//! Caller-tunable knobs for [`elicit_with`](crate::elicit_with).

use std::path::PathBuf;
use std::time::Duration;

/// Optional overrides for an [`elicit`](crate::elicit) call.
#[derive(Debug, Clone, Default)]
pub struct ElicitOptions {
    /// Renderer selection. Default: [`RendererPreference::AutoGui`].
    pub renderer: RendererPreference,

    /// Per-call timeout. If `None`, uses [`PromptSpec::timeout_secs`](crate::PromptSpec::timeout_secs).
    pub timeout: Option<Duration>,

    /// Working directory used to resolve relative paths (e.g., custom icons).
    /// If `None`, the process's current working directory is used.
    pub working_dir: Option<PathBuf>,

    /// Parent PID — used by the platform renderer to focus-steal the
    /// popup window so it appears on top of the parent terminal.
    pub parent_pid: Option<u32>,
}

/// Which renderer to use.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub enum RendererPreference {
    /// Pick GUI if a display is available; otherwise TUI.
    ///
    /// This is the default and what most callers want. It detects SSH
    /// sessions (no X forwarding) and CI environments and falls back to TUI
    /// automatically.
    #[default]
    AutoGui,

    /// Always use the OS-native GUI; fail loudly with
    /// [`ElicitError::NoRenderer`](crate::ElicitError::NoRenderer) if
    /// unavailable.
    ///
    /// Use this when the agent requires the modal-blocking guarantee of a
    /// native popup and will not accept a TUI fallback.
    ForceGui,

    /// Always use the terminal fallback (`inquire`).
    ///
    /// Use this for CI smoke tests, scripted automation, or when running
    /// over SSH without X forwarding.
    ForceTty,
}