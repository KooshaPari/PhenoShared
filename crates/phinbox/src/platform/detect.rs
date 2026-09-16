//! Platform and renderer detection.

use crate::options::RendererPreference;
use serde::{Deserialize, Serialize};

/// The OS the binary is running on.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Platform {
    /// macOS (any version, including aarch64).
    Macos,
    /// Windows (any version).
    Windows,
    /// Linux (any distro).
    Linux,
    /// Other / unknown (e.g., BSD). The crate will refuse to render a
    /// native GUI and fall back to TUI.
    Unknown,
}

/// What kind of renderer would be used for a given preference.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RendererKind {
    /// OS-native GUI popup.
    Gui,
    /// Terminal-based (inquire) fallback.
    Tty,
    /// No renderer available (e.g., TTY-less environment with `ForceGui`).
    None,
}

/// Detect the running platform (compile-time).
#[must_use]
pub fn detect() -> Platform {
    #[cfg(target_os = "macos")]
    {
        Platform::Macos
    }
    #[cfg(target_os = "windows")]
    {
        Platform::Windows
    }
    #[cfg(target_os = "linux")]
    {
        Platform::Linux
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    {
        Platform::Unknown
    }
}

/// Detect which renderer would be used right now.
///
/// Detection rules (in order):
/// 1. `ForceGui` → Gui (caller must accept failure if no display).
/// 2. `ForceTty` → Tty.
/// 3. `AutoGui`:
///    - CI env (`$CI` set) → Tty.
///    - SSH session with no `$DISPLAY` / `$WAYLAND_DISPLAY` → Tty.
///    - Display available → Gui.
///    - Otherwise → Tty.
#[must_use]
pub fn detect_renderer(pref: RendererPreference) -> RendererKind {
    match pref {
        RendererPreference::ForceGui => RendererKind::Gui,
        RendererPreference::ForceTty => RendererKind::Tty,
        RendererPreference::AutoGui => {
            let is_ci = std::env::var_os("CI").is_some();
            let is_ssh = std::env::var_os("SSH_CLIENT").is_some()
                || std::env::var_os("SSH_TTY").is_some();
            let has_display = std::env::var_os("DISPLAY").is_some()
                || std::env::var_os("WAYLAND_DISPLAY").is_some();

            if is_ci || (is_ssh && !has_display) {
                RendererKind::Tty
            } else if has_display {
                RendererKind::Gui
            } else {
                RendererKind::Tty
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // We can't easily change the env from a multi-threaded test, but we can
    // verify the pure-function behavior on the current platform.

    #[test]
    fn force_gui_returns_gui() {
        assert_eq!(
            detect_renderer(RendererPreference::ForceGui),
            RendererKind::Gui
        );
    }

    #[test]
    fn force_tty_returns_tty() {
        assert_eq!(
            detect_renderer(RendererPreference::ForceTty),
            RendererKind::Tty
        );
    }

    #[test]
    fn auto_returns_one_of_tty_or_gui() {
        let r = detect_renderer(RendererPreference::AutoGui);
        assert!(matches!(r, RendererKind::Gui | RendererKind::Tty));
    }

    #[test]
    fn detect_is_a_known_platform() {
        let p = detect();
        assert!(matches!(
            p,
            Platform::Macos | Platform::Windows | Platform::Linux | Platform::Unknown
        ));
    }
}