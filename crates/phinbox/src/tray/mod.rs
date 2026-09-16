//! OS tray icon — status bar item on macOS, notification area on Windows,
//! libappindicator on Linux. Gated behind `--features tray-native`.
//!
//! When the feature is disabled, or when running headless (CI, SSH, no DISPLAY),
//! the module exposes a [`NoopTray`] that satisfies the same trait surface
//! without touching the OS. This keeps the daemon's tray wiring unconditional
//! at the call site — there's a single `TrayHandle` regardless of backend.

use std::fmt;
use std::path::PathBuf;
use std::sync::Arc;

use serde::{Deserialize, Serialize};

/// User-visible action triggered from the tray icon.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum TrayEvent {
    /// User left-clicked (or activated) the tray icon.
    Click,
    /// User double-clicked the tray icon.
    DoubleClick,
    /// User picked a menu item by id.
    MenuItem { id: String },
}

/// Predefined menu items the tray exposes. Stable ids so callers can dispatch.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MenuAction {
    /// Open the inbox browser view in the default browser.
    OpenInbox,
    /// Foreground the local daemon (open the inbox URL in the browser).
    OpenLatest,
    /// Toggle quiet mode (no notifications until un-toggled).
    ToggleQuiet,
    /// Quit the daemon gracefully.
    Quit,
}

impl MenuAction {
    /// Stable menu item id for this action.
    #[must_use]
    pub fn id(self) -> &'static str {
        match self {
            MenuAction::OpenInbox => "tray.open_inbox",
            MenuAction::OpenLatest => "tray.open_latest",
            MenuAction::ToggleQuiet => "tray.toggle_quiet",
            MenuAction::Quit => "tray.quit",
        }
    }

    /// Human label for the menu item.
    #[must_use]
    pub fn label(self) -> &'static str {
        match self {
            MenuAction::OpenInbox => "Open Inbox…",
            MenuAction::OpenLatest => "Open Latest Request",
            MenuAction::ToggleQuiet => "Pause Notifications",
            MenuAction::Quit => "Quit phinbox daemon",
        }
    }
}

/// Builder for the tray icon. Backend is selected at compile time.
#[derive(Debug, Clone)]
pub struct TrayConfig {
    /// Tooltip shown on hover / long-press.
    pub tooltip: String,
    /// Initial badge / title text (e.g. "3" for 3 pending).
    pub initial_badge: String,
    /// Inbox root path — used by `OpenLatest` to pick the most-recent pending.
    pub inbox_root: PathBuf,
    /// URL the daemon serves on (used by `OpenInbox` / `OpenLatest`).
    pub inbox_url: String,
    /// Whether to start with sound (default false).
    pub quiet: bool,
}

impl TrayConfig {
    /// Build a sane default config from the daemon's actual bind URL + inbox root.
    pub fn new(inbox_url: impl Into<String>, inbox_root: impl Into<PathBuf>) -> Self {
        Self {
            tooltip: "phinbox inbox".into(),
            initial_badge: String::new(),
            inbox_root: inbox_root.into(),
            inbox_url: inbox_url.into(),
            quiet: false,
        }
    }
}

/// Result of tray construction.
pub type TrayResult<T> = Result<T, TrayError>;

#[derive(Debug)]
pub enum TrayError {
    /// The OS reported the tray is unavailable (no UI session, headless SSH, etc.)
    NotAvailable(String),
    /// Icon-image encoding failed.
    Icon(String),
    /// Some other OS error.
    Backend(String),
}

impl fmt::Display for TrayError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TrayError::NotAvailable(s) => write!(f, "tray unavailable: {s}"),
            TrayError::Icon(s) => write!(f, "icon error: {s}"),
            TrayError::Backend(s) => write!(f, "tray backend error: {s}"),
        }
    }
}

impl std::error::Error for TrayError {}

/// Trait shared by [`NoopTray`] and the real native tray handle.
pub trait Tray: Send + Sync {
    /// Update the badge text (count of pending requests shown next to the icon).
    fn set_badge(&self, text: &str) -> TrayResult<()>;
    /// Update the tooltip on hover / long-press.
    fn set_tooltip(&self, text: &str) -> TrayResult<()>;
    /// Show a transient balloon notification.
    fn notify(&self, title: &str, body: &str) -> TrayResult<()>;
    /// Try to receive the next tray event without blocking.
    fn try_recv(&self) -> Option<TrayEvent>;
    /// Shut down the tray (icon disappears, listener thread exits).
    fn shutdown(&self) -> TrayResult<()>;
    /// Backend name for diagnostics.
    fn backend_name(&self) -> &'static str;
    /// The URL the daemon is bound to (used by click handlers to open
    /// the right inbox in the default browser).
    fn inbox_url(&self) -> Option<&str> {
        None
    }
    /// Poll for pending tray events and forward them to the event channel.
    /// On macOS, this must be called from the main thread (`NSRunLoop`).
    /// On other platforms, this is a no-op (events arrive via the channel).
    fn poll(&self) {}
}

/// Construct a tray matching the compile-time feature set.
pub fn build_tray(cfg: TrayConfig) -> TrayResult<Arc<dyn Tray>> {
    #[cfg(feature = "tray-native")]
    {
        match native::create_native_tray(cfg.clone()) {
            Ok(t) => Ok(t),
            Err(e) => {
                tracing::warn!(error = %e, "tray-native build failed; falling back to NoopTray");
                Ok(Arc::new(NoopTray::new(cfg)))
            }
        }
    }

    #[cfg(not(feature = "tray-native"))]
    {
        let _ = cfg;
        Ok(Arc::new(NoopTray::new(cfg)))
    }
}

// ============================================================================
// NoopTray — the always-available fallback
// ============================================================================

/// Tray implementation that does nothing. Used when `tray-native` is off,
/// the native backend couldn't attach, or the daemon was launched with
/// `--no-tray`.
#[derive(Debug)]
pub struct NoopTray {
    #[allow(dead_code)]
    cfg: TrayConfig,
}

impl NoopTray {
    #[must_use]
    pub fn new(cfg: TrayConfig) -> Self {
        Self { cfg }
    }
}

impl Tray for NoopTray {
    fn set_badge(&self, _text: &str) -> TrayResult<()> {
        Ok(())
    }
    fn set_tooltip(&self, _text: &str) -> TrayResult<()> {
        Ok(())
    }
    fn notify(&self, _title: &str, _body: &str) -> TrayResult<()> {
        Ok(())
    }
    fn try_recv(&self) -> Option<TrayEvent> {
        None
    }
    fn shutdown(&self) -> TrayResult<()> {
        Ok(())
    }
    fn backend_name(&self) -> &'static str {
        "noop"
    }
    fn inbox_url(&self) -> Option<&str> {
        Some(&self.cfg.inbox_url)
    }
}

// ============================================================================
// Native backend — compiled only with --features tray-native
// ============================================================================

#[cfg(feature = "tray-native")]
mod native;
#[cfg(feature = "tray-native")]
pub use native::poll_tray;

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn menu_action_ids_are_stable() {
        assert_eq!(MenuAction::OpenInbox.id(), "tray.open_inbox");
        assert_eq!(MenuAction::OpenLatest.id(), "tray.open_latest");
        assert_eq!(MenuAction::ToggleQuiet.id(), "tray.toggle_quiet");
        assert_eq!(MenuAction::Quit.id(), "tray.quit");
    }

    #[test]
    fn menu_action_serde_round_trips() {
        for a in [
            MenuAction::OpenInbox,
            MenuAction::OpenLatest,
            MenuAction::ToggleQuiet,
            MenuAction::Quit,
        ] {
            let s = serde_json::to_string(&a).unwrap();
            let back: MenuAction = serde_json::from_str(&s).unwrap();
            assert_eq!(back, a);
        }
    }

    #[test]
    fn tray_event_serde_tagged() {
        let click = TrayEvent::Click;
        let s = serde_json::to_string(&click).unwrap();
        assert!(s.contains("\"kind\":\"click\""));

        let item = TrayEvent::MenuItem {
            id: "tray.quit".into(),
        };
        let s = serde_json::to_string(&item).unwrap();
        assert!(s.contains("\"kind\":\"menu_item\""));
        assert!(s.contains("\"id\":\"tray.quit\""));
    }

    #[test]
    fn noop_tray_is_a_noop() {
        let tray = NoopTray::new(TrayConfig::new(
            "http://127.0.0.1:7117",
            "/tmp/inbox",
        ));
        assert_eq!(tray.backend_name(), "noop");
        assert!(tray.set_badge("5").is_ok());
        assert!(tray.set_tooltip("hi").is_ok());
        assert!(tray.notify("t", "b").is_ok());
        assert!(tray.shutdown().is_ok());
        assert!(tray.try_recv().is_none());
    }

    #[test]
    fn build_tray_returns_something() {
        let t = build_tray(TrayConfig::new(
            "http://127.0.0.1:7117",
            "/tmp/inbox",
        ));
        let t = match t {
            Ok(t) => t,
            Err(TrayError::NotAvailable(_)) => return, // headless CI
            Err(e) => panic!("unexpected: {e}"),
        };
        assert!(t.set_badge("3").is_ok());
        assert!(t.set_tooltip("hi").is_ok());
        assert!(t.notify("t", "b").is_ok());
    }

    #[test]
    fn tray_config_fields_default() {
        let cfg = TrayConfig::new("http://localhost:7117", "/tmp/inbox");
        assert_eq!(cfg.tooltip, "phinbox inbox");
        assert!(cfg.initial_badge.is_empty());
        assert!(!cfg.quiet);
    }

    #[test]
    fn tray_error_display() {
        let e = TrayError::NotAvailable("no display".into());
        assert_eq!(e.to_string(), "tray unavailable: no display");
        let e = TrayError::Icon("bad rgba".into());
        assert_eq!(e.to_string(), "icon error: bad rgba");
        let e = TrayError::Backend("boom".into());
        assert_eq!(e.to_string(), "tray backend error: boom");
    }
}
