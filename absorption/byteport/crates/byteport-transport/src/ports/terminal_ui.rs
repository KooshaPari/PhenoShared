//! Terminal-backed [`UiPort`](super::ui::UiPort) adapter.
//!
//! `TerminalUiAdapter` renders views and prompts using only the standard
//! library: views and most prompts are written to stdout via
//! `writeln!`, `Warning` / `Error` prompts are echoed to stderr, and the
//! user's response is read from stdin with the standard `BufRead` API.
//!
//! The adapter deliberately avoids new dependencies. The surrounding
//! transport crate depends only on `serde` and `thiserror`, and adding
//! a TUI crate such as `crossterm` would expand that surface for a
//! presentation concern that is intentionally pluggable. Production
//! user interfaces should swap in a richer adapter (TUI, web, native
//! window) that implements the same `UiPort` trait.

use std::io::{self, BufRead, Write};

use crate::ports::ui::{PromptKind, PromptMessage, PromptResponse, UiError, UiPort, UiView};

/// A `UiPort` adapter that writes to the process's stdout / stderr and
/// reads responses from stdin.
///
/// `Info`, `Confirm`, `Choice`, and `Input` prompts write to stdout;
/// `Warning` and `Error` prompts are mirrored to stderr so they remain
/// visible when stdout is captured (e.g. by a CI runner or a parent
/// process piping output).
///
/// # Interactive vs. non-interactive
///
/// [`TerminalUiAdapter::new`] returns an interactive adapter that
/// blocks on stdin for every prompt. In unattended contexts (CI,
/// smoke runs, server-side job runners) this would hang the process,
/// so the adapter exposes [`TerminalUiAdapter::non_interactive`]. The
/// non-interactive variant returns `Err(UiError::UserCancelled)` for
/// every prompt without reading stdin, which is the safest default
/// for environments that have no operator to answer.
#[derive(Debug, Clone, Default)]
pub struct TerminalUiAdapter {
    non_interactive: bool,
}

impl TerminalUiAdapter {
    /// Build an interactive adapter that reads responses from stdin.
    pub fn new() -> Self {
        Self::default()
    }

    /// Build a non-interactive adapter. Every prompt returns
    /// `Err(UiError::UserCancelled)` without reading from stdin.
    pub fn non_interactive() -> Self {
        Self { non_interactive: true }
    }

    /// Returns `true` when the adapter will short-circuit every
    /// prompt with `UiError::UserCancelled`.
    pub fn is_non_interactive(&self) -> bool {
        self.non_interactive
    }

    /// Render the section header used for [`UiPort::show`].
    ///
    /// The view enum carries no data; the adapter can only emit a
    /// header. Concrete content rendering is the responsibility of
    /// the caller, which can use a follow-up `println!` or a separate
    /// rendering port.
    pub fn render_view(view: &UiView) -> &'static str {
        match view {
            UiView::Dashboard => "=== Dashboard ===",
            UiView::DeviceList => "=== Device List ===",
            UiView::TestResults => "=== Test Results ===",
            UiView::Settings => "=== Settings ===",
        }
    }

    /// Short, lower-case label used to prefix a prompt.
    pub fn kind_label(kind: &PromptKind) -> &'static str {
        match kind {
            PromptKind::Info => "info",
            PromptKind::Warning => "warning",
            PromptKind::Error => "error",
            PromptKind::Confirm => "confirm",
            PromptKind::Choice => "choice",
            PromptKind::Input => "input",
        }
    }

    /// Parse the user's text response to a [`PromptKind::Confirm`]
    /// prompt. Recognises `"y"` / `"yes"` (case-insensitive) as `true`;
    /// anything else (including an empty line) is treated as `false`.
    pub fn parse_confirm(text: &str) -> PromptResponse {
        let normalized = text.trim().to_ascii_lowercase();
        PromptResponse::Confirmed(matches!(normalized.as_str(), "y" | "yes"))
    }

    /// Parse the user's text response to a [`PromptKind::Choice`]
    /// prompt. The input is interpreted as a zero-based index into
    /// `options`. Returns `Err(UiError::InvalidState)` for non-numeric
    /// input or out-of-range indices.
    pub fn parse_choice(text: &str, options: &[String]) -> Result<PromptResponse, UiError> {
        let idx: usize = text.trim().parse().map_err(|_| UiError::InvalidState)?;
        if idx >= options.len() {
            return Err(UiError::InvalidState);
        }
        Ok(PromptResponse::Selected(idx))
    }

    /// Parse the user's text response to a [`PromptKind::Input`]
    /// prompt. Empty / whitespace-only input falls back to `default`
    /// when provided.
    pub fn parse_input(text: &str, default: Option<&str>) -> PromptResponse {
        let trimmed = text.trim();
        if trimmed.is_empty() {
            if let Some(default) = default {
                return PromptResponse::Input(default.to_string());
            }
        }
        PromptResponse::Input(trimmed.to_string())
    }

    fn write_prompt(&self, msg: &PromptMessage) -> Result<(), UiError> {
        let to_stderr = matches!(msg.kind, PromptKind::Warning | PromptKind::Error);
        let label = Self::kind_label(&msg.kind);
        if to_stderr {
            let mut err = io::stderr().lock();
            writeln!(err, "[{label}] {}\n{}", msg.title, msg.body)
                .map_err(|e| UiError::RenderFailed(format!("write to stderr failed: {e}")))?;
            err.flush()
                .map_err(|e| UiError::RenderFailed(format!("flush stderr failed: {e}")))?;
        } else {
            let mut out = io::stdout().lock();
            writeln!(out, "[{label}] {}\n{}", msg.title, msg.body)
                .map_err(|e| UiError::RenderFailed(format!("write to stdout failed: {e}")))?;
            out.flush()
                .map_err(|e| UiError::RenderFailed(format!("flush stdout failed: {e}")))?;
        }
        Ok(())
    }
}

impl UiPort for TerminalUiAdapter {
    fn show(&self, view: &UiView) -> Result<(), UiError> {
        let header = Self::render_view(view);
        let mut out = io::stdout().lock();
        writeln!(out, "{header}").map_err(|e| UiError::RenderFailed(format!("write to stdout failed: {e}")))?;
        out.flush()
            .map_err(|e| UiError::RenderFailed(format!("flush stdout failed: {e}")))?;
        Ok(())
    }

    fn prompt(&self, msg: &PromptMessage) -> Result<PromptResponse, UiError> {
        if self.non_interactive {
            return Err(UiError::UserCancelled);
        }

        self.write_prompt(msg)?;

        let stdin = io::stdin();
        let mut handle = stdin.lock();
        let mut line = String::new();
        handle
            .read_line(&mut line)
            .map_err(|e| UiError::RenderFailed(format!("read from stdin failed: {e}")))?;

        match msg.kind {
            PromptKind::Info | PromptKind::Warning | PromptKind::Error => Ok(PromptResponse::Acknowledge),
            PromptKind::Confirm => Ok(Self::parse_confirm(&line)),
            PromptKind::Choice => Self::parse_choice(&line, &msg.options),
            PromptKind::Input => Ok(Self::parse_input(&line, msg.default.as_deref())),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_view_matches_each_variant() {
        assert_eq!(TerminalUiAdapter::render_view(&UiView::Dashboard), "=== Dashboard ===");
        assert_eq!(
            TerminalUiAdapter::render_view(&UiView::DeviceList),
            "=== Device List ==="
        );
        assert_eq!(
            TerminalUiAdapter::render_view(&UiView::TestResults),
            "=== Test Results ==="
        );
        assert_eq!(TerminalUiAdapter::render_view(&UiView::Settings), "=== Settings ===");
    }

    #[test]
    fn kind_label_matches_each_variant() {
        assert_eq!(TerminalUiAdapter::kind_label(&PromptKind::Info), "info");
        assert_eq!(TerminalUiAdapter::kind_label(&PromptKind::Warning), "warning");
        assert_eq!(TerminalUiAdapter::kind_label(&PromptKind::Error), "error");
        assert_eq!(TerminalUiAdapter::kind_label(&PromptKind::Confirm), "confirm");
        assert_eq!(TerminalUiAdapter::kind_label(&PromptKind::Choice), "choice");
        assert_eq!(TerminalUiAdapter::kind_label(&PromptKind::Input), "input");
    }

    #[test]
    fn parse_confirm_recognises_yes_variants() {
        assert_eq!(TerminalUiAdapter::parse_confirm("y"), PromptResponse::Confirmed(true));
        assert_eq!(TerminalUiAdapter::parse_confirm("Y"), PromptResponse::Confirmed(true));
        assert_eq!(TerminalUiAdapter::parse_confirm("yes"), PromptResponse::Confirmed(true));
        assert_eq!(TerminalUiAdapter::parse_confirm("YES"), PromptResponse::Confirmed(true));
        assert_eq!(
            TerminalUiAdapter::parse_confirm("  y  "),
            PromptResponse::Confirmed(true)
        );
    }

    #[test]
    fn parse_confirm_treats_other_input_as_no() {
        assert_eq!(TerminalUiAdapter::parse_confirm("n"), PromptResponse::Confirmed(false));
        assert_eq!(TerminalUiAdapter::parse_confirm("no"), PromptResponse::Confirmed(false));
        assert_eq!(TerminalUiAdapter::parse_confirm(""), PromptResponse::Confirmed(false));
        assert_eq!(
            TerminalUiAdapter::parse_confirm("maybe"),
            PromptResponse::Confirmed(false)
        );
    }

    #[test]
    fn parse_choice_returns_index_in_range() {
        let options = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        assert_eq!(
            TerminalUiAdapter::parse_choice("0", &options).unwrap(),
            PromptResponse::Selected(0)
        );
        assert_eq!(
            TerminalUiAdapter::parse_choice("2", &options).unwrap(),
            PromptResponse::Selected(2)
        );
        assert_eq!(
            TerminalUiAdapter::parse_choice("  1  ", &options).unwrap(),
            PromptResponse::Selected(1)
        );
    }

    #[test]
    fn parse_choice_rejects_out_of_range() {
        let options = vec!["a".to_string(), "b".to_string()];
        assert_eq!(
            TerminalUiAdapter::parse_choice("5", &options),
            Err(UiError::InvalidState)
        );
    }

    #[test]
    fn parse_choice_rejects_non_numeric() {
        let options = vec!["a".to_string(), "b".to_string()];
        assert_eq!(
            TerminalUiAdapter::parse_choice("first", &options),
            Err(UiError::InvalidState)
        );
    }

    #[test]
    fn parse_input_returns_trimmed_text() {
        assert_eq!(
            TerminalUiAdapter::parse_input("hello", None),
            PromptResponse::Input("hello".to_string())
        );
        assert_eq!(
            TerminalUiAdapter::parse_input("  hello  ", None),
            PromptResponse::Input("hello".to_string())
        );
    }

    #[test]
    fn parse_input_falls_back_to_default_when_empty() {
        assert_eq!(
            TerminalUiAdapter::parse_input("", Some("fallback")),
            PromptResponse::Input("fallback".to_string())
        );
        assert_eq!(
            TerminalUiAdapter::parse_input("   ", Some("fallback")),
            PromptResponse::Input("fallback".to_string())
        );
    }

    #[test]
    fn parse_input_empty_without_default_returns_empty() {
        assert_eq!(
            TerminalUiAdapter::parse_input("", None),
            PromptResponse::Input("".to_string())
        );
    }

    #[test]
    fn parse_input_explicit_text_overrides_default() {
        assert_eq!(
            TerminalUiAdapter::parse_input("override", Some("fallback")),
            PromptResponse::Input("override".to_string())
        );
    }

    #[test]
    fn non_interactive_factory_sets_flag() {
        let ui = TerminalUiAdapter::non_interactive();
        assert!(ui.is_non_interactive());
    }

    #[test]
    fn new_factory_is_interactive() {
        let ui = TerminalUiAdapter::new();
        assert!(!ui.is_non_interactive());
    }

    #[test]
    fn non_interactive_returns_user_cancelled_for_every_kind() {
        let ui = TerminalUiAdapter::non_interactive();
        let info = PromptMessage::info("t", "b");
        let warning = PromptMessage::warning("t", "b");
        let error = PromptMessage::error("t", "b");
        let confirm = PromptMessage::confirm("t", "b");
        let choice = PromptMessage::choice("t", "b", vec!["a".to_string()]);
        let input = PromptMessage::input("t", "b", None);
        assert_eq!(ui.prompt(&info), Err(UiError::UserCancelled));
        assert_eq!(ui.prompt(&warning), Err(UiError::UserCancelled));
        assert_eq!(ui.prompt(&error), Err(UiError::UserCancelled));
        assert_eq!(ui.prompt(&confirm), Err(UiError::UserCancelled));
        assert_eq!(ui.prompt(&choice), Err(UiError::UserCancelled));
        assert_eq!(ui.prompt(&input), Err(UiError::UserCancelled));
    }
}
