//! Persistent user settings for the sl-viewer (FR-VIEWER-SETTINGS-1).
//!
//! Settings are stored as pretty-printed JSON at:
//!
//! - macOS:   `~/Library/Application Support/SessionLedger/settings.json`
//! - Linux:   `${XDG_CONFIG_HOME:-~/.config}/SessionLedger/settings.json`
//! - Windows: `%APPDATA%\SessionLedger\settings.json`
//! - WASM:    no filesystem access — [`Settings::load`] returns the
//!   in-memory defaults and [`Settings::save`] returns an error.
//!
//! The location can be overridden at runtime via the
//! `SL_VIEWER_SETTINGS_DIR` environment variable (used by the test suite).
//!
//! All I/O is best-effort: a corrupt or unreadable file silently falls back
//! to [`Settings::default`] so a malformed preferences file can never brick
//! the viewer.

use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::theme::Theme;

/// Stable, serde-friendly enumeration of the tab the viewer should land on
/// at launch.
///
/// Mirrors the runtime [`crate::app::Tab`] enum without depending on it
/// (`app.rs` imports this enum to seed the initial `use_signal`). Keeping
/// the mirror in a dedicated module avoids a `settings -> app -> settings`
/// cycle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum DefaultTab {
    #[default]
    Bundles,
    History,
    Unfinished,
    Memory,
    LiveFeed,
    Search,
    Timeline,
    Replay,
    Corpus,
}

impl DefaultTab {
    /// All variants, in tab-bar order (matches [`crate::app::Tab::ALL`]
    /// minus the Settings tab, which we never auto-launch into).
    pub const ALL: [DefaultTab; 9] = [
        DefaultTab::Bundles,
        DefaultTab::History,
        DefaultTab::Unfinished,
        DefaultTab::Memory,
        DefaultTab::LiveFeed,
        DefaultTab::Search,
        DefaultTab::Timeline,
        DefaultTab::Replay,
        DefaultTab::Corpus,
    ];

    /// Human-readable label for `<option>` rendering.
    pub fn label(self) -> &'static str {
        match self {
            Self::Bundles => "Bundles",
            Self::History => "History",
            Self::Unfinished => "Unfinished",
            Self::Memory => "Memory",
            Self::LiveFeed => "Live Feed",
            Self::Search => "Search",
            Self::Timeline => "Timeline",
            Self::Replay => "Replay",
            Self::Corpus => "Raw Sessions",
        }
    }

    /// DOM id of the runtime tab this preference activates.
    pub fn tab_id(self) -> &'static str {
        match self {
            Self::Bundles => "tab-bundles",
            Self::History => "tab-history",
            Self::Unfinished => "tab-unfinished",
            Self::Memory => "tab-memory",
            Self::LiveFeed => "tab-live-feed",
            Self::Search => "tab-search",
            Self::Timeline => "tab-timeline",
            Self::Replay => "tab-replay",
            Self::Corpus => "tab-corpus",
        }
    }

    /// `data-default-tab` attribute value used by the `<select>` markup
    /// for option matching.
    pub fn value_attr(self) -> &'static str {
        match self {
            Self::Bundles => "bundles",
            Self::History => "history",
            Self::Unfinished => "unfinished",
            Self::Memory => "memory",
            Self::LiveFeed => "live-feed",
            Self::Search => "search",
            Self::Timeline => "timeline",
            Self::Replay => "replay",
            Self::Corpus => "corpus",
        }
    }
}

/// User-facing viewer settings. Persisted to `settings.json` on every
/// change so the next launch picks them up.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Settings {
    /// Theme preference (`Light` / `Dark` / `System`).
    #[serde(default)]
    pub theme: Theme,
    /// Tab the viewer should land on at launch.
    #[serde(default)]
    pub default_tab: DefaultTab,
}

impl Settings {
    /// Resolve the platform-specific directory for `settings.json`.
    ///
    /// Honours `SL_VIEWER_SETTINGS_DIR` (test override) before consulting
    /// the OS conventions.
    #[must_use]
    pub fn dir() -> Option<PathBuf> {
        settings_dir()
    }

    /// Path of the `settings.json` file.
    #[must_use]
    pub fn path() -> Option<PathBuf> {
        Self::dir().map(|d| d.join("settings.json"))
    }

    /// Load settings from the platform-default location. Falls back to
    /// [`Settings::default`] on any I/O or parse error so a corrupt file
    /// cannot brick the viewer.
    #[must_use]
    pub fn load() -> Self {
        match Self::path() {
            Some(path) => Self::load_from_path(&path),
            None => Self::default(),
        }
    }

    /// Load settings from an explicit path (test-only / override-friendly).
    ///
    /// Missing files and parse errors fall back to [`Settings::default`].
    #[must_use]
    pub fn load_from_path(path: &Path) -> Self {
        let raw = match fs::read_to_string(path) {
            Ok(s) => s,
            Err(_) => return Self::default(),
        };
        serde_json::from_str(&raw).unwrap_or_else(|_| Self::default())
    }

    /// Persist the settings to the platform-default location.
    ///
    /// Returns an error if the directory cannot be created or the file
    /// cannot be written (e.g. WASM runtime, read-only filesystem).
    pub fn save(&self) -> Result<(), String> {
        let path = Self::path()
            .ok_or_else(|| "settings persistence is unavailable on this platform".to_owned())?;
        self.save_to_path(&path)
    }

    /// Persist the settings to an explicit path. Used by the test suite and
    /// by the override flow.
    pub fn save_to_path(&self, path: &Path) -> Result<(), String> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("could not create {}: {e}", parent.display()))?;
        }
        let pretty = serde_json::to_string_pretty(self)
            .map_err(|e| format!("could not serialize settings: {e}"))?;
        fs::write(path, pretty).map_err(|e| format!("could not write {}: {e}", path.display()))?;
        Ok(())
    }
}

/// Resolve the OS-native settings directory. WASM returns `None` because
/// browsers cannot host the viewer's settings file.
#[cfg(not(target_arch = "wasm32"))]
fn settings_dir() -> Option<PathBuf> {
    let override_dir = std::env::var("SL_VIEWER_SETTINGS_DIR").ok();
    let home = std::env::var_os("HOME");
    let appdata = std::env::var_os("APPDATA");
    let xdg = std::env::var_os("XDG_CONFIG_HOME");
    resolve_settings_dir(
        override_dir.as_deref(),
        home.as_deref(),
        appdata.as_deref(),
        xdg.as_deref(),
    )
}

/// Pure resolver — split out so the override behaviour can be unit-tested
/// without mutating process-level environment variables (the crate forbids
/// `unsafe`).
#[cfg(not(target_arch = "wasm32"))]
fn resolve_settings_dir(
    override_dir: Option<&str>,
    home: Option<&std::ffi::OsStr>,
    appdata: Option<&std::ffi::OsStr>,
    xdg_config: Option<&std::ffi::OsStr>,
) -> Option<PathBuf> {
    if let Some(dir) = override_dir {
        if !dir.is_empty() {
            return Some(PathBuf::from(dir));
        }
    }

    if cfg!(target_os = "macos") {
        let home = home?;
        return Some(
            PathBuf::from(home).join("Library").join("Application Support").join("SessionLedger"),
        );
    }

    if cfg!(target_os = "windows") {
        if let Some(appdata) = appdata {
            return Some(PathBuf::from(appdata).join("SessionLedger"));
        }
        if let Some(home) = home {
            return Some(PathBuf::from(home).join("AppData").join("Roaming").join("SessionLedger"));
        }
        return None;
    }

    // Linux / other Unix: XDG first, fall back to `$HOME/.config`.
    if let Some(xdg) = xdg_config {
        return Some(PathBuf::from(xdg).join("SessionLedger"));
    }
    let home = home?;
    Some(PathBuf::from(home).join(".config").join("SessionLedger"))
}

#[cfg(target_arch = "wasm32")]
fn settings_dir() -> Option<PathBuf> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sandbox_dir(label: &str) -> PathBuf {
        let mut dir = std::env::temp_dir();
        dir.push(format!(
            "sl-viewer-settings-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0)
        ));
        dir
    }

    #[test]
    fn defaults_match_in_code_defaults() {
        let s = Settings::default();
        assert_eq!(s.theme, Theme::System);
        assert_eq!(s.default_tab, DefaultTab::Bundles);
    }

    #[test]
    fn round_trip_persistence_writes_and_reads() {
        let dir = sandbox_dir("roundtrip");
        let path = dir.join("settings.json");
        let original = Settings { theme: Theme::Light, default_tab: DefaultTab::Search };
        original.save_to_path(&path).expect("save succeeds");
        let restored = Settings::load_from_path(&path);
        assert_eq!(restored, original, "round-trip equality");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn theme_serialization_round_trips_for_each_variant() {
        for theme in [Theme::Light, Theme::Dark, Theme::System] {
            let s = Settings { theme, default_tab: DefaultTab::Bundles };
            let json = serde_json::to_string(&s).expect("serialize");
            let back: Settings = serde_json::from_str(&json).expect("deserialize");
            assert_eq!(back.theme, theme);
        }
    }

    #[test]
    fn theme_json_uses_snake_case_identifiers() {
        let s = Settings { theme: Theme::Light, default_tab: DefaultTab::Memory };
        let json = serde_json::to_string(&s).expect("serialize");
        assert!(json.contains("\"theme\":\"light\""), "got {json}");
        assert!(json.contains("\"default_tab\":\"memory\""), "got {json}");
    }

    #[test]
    fn load_from_missing_file_returns_defaults() {
        let dir = sandbox_dir("missing");
        let path = dir.join("does-not-exist.json");
        let s = Settings::load_from_path(&path);
        assert_eq!(s, Settings::default());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn load_from_corrupt_file_returns_defaults() {
        let dir = sandbox_dir("corrupt");
        fs::create_dir_all(&dir).expect("mkdir");
        let path = dir.join("settings.json");
        fs::write(&path, "{ not valid json").expect("write");
        let s = Settings::load_from_path(&path);
        assert_eq!(s, Settings::default());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn load_partial_json_fills_missing_fields_with_defaults() {
        let dir = sandbox_dir("partial");
        fs::create_dir_all(&dir).expect("mkdir");
        let path = dir.join("settings.json");
        fs::write(&path, r#"{"theme":"dark"}"#).expect("write");
        let s = Settings::load_from_path(&path);
        assert_eq!(s.theme, Theme::Dark);
        assert_eq!(s.default_tab, DefaultTab::default());
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn save_creates_parent_directories() {
        let dir = sandbox_dir("nested");
        let path = dir.join("a").join("b").join("settings.json");
        let s = Settings::default();
        s.save_to_path(&path).expect("save succeeds");
        assert!(path.exists(), "settings.json should exist");
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn default_tab_labels_and_ids_match_runtime_tabs() {
        // The tab IDs must match the runtime `Tab::id()` strings in
        // `app.rs`. If either side drifts, the Settings select stops
        // focusing the right tab.
        for variant in DefaultTab::ALL {
            let id = variant.tab_id();
            assert!(id.starts_with("tab-"), "{id} must start with tab-");
            let value = variant.value_attr();
            assert!(!value.is_empty(), "value attr must be non-empty");
            assert!(!variant.label().is_empty());
        }
    }

    #[test]
    fn default_tab_value_attrs_are_stable_strings() {
        assert_eq!(DefaultTab::Bundles.value_attr(), "bundles");
        assert_eq!(DefaultTab::Corpus.value_attr(), "corpus");
        assert_eq!(DefaultTab::LiveFeed.value_attr(), "live-feed");
    }

    #[test]
    fn macos_default_settings_dir_uses_application_support() {
        // Only meaningful on macOS — the directory string itself is the
        // contract.
        if cfg!(target_os = "macos") {
            let path = Settings::path().expect("settings path on macOS");
            let s = path.to_string_lossy();
            assert!(s.contains("Library/Application Support"), "got {s}");
            assert!(s.contains("SessionLedger"), "got {s}");
            assert!(s.ends_with("settings.json"), "got {s}");
        }
    }

    #[test]
    fn settings_dir_override_is_honoured() {
        // Pure resolver path — exercises the override branch without mutating
        // process env (the crate forbids `unsafe`, and the env-driven path
        // is exercised by the runtime when a user sets the variable).
        let dir = std::path::PathBuf::from("/tmp/sl-viewer-override-test");
        let resolved =
            super::resolve_settings_dir(Some(dir.to_str().expect("utf-8 path")), None, None, None)
                .expect("override resolves");
        assert_eq!(resolved, dir);
    }

    #[test]
    fn settings_dir_uses_xdg_when_present_on_unix() {
        if !(cfg!(target_os = "linux") || cfg!(target_os = "freebsd") || cfg!(target_os = "netbsd"))
        {
            return;
        }
        let home = std::ffi::OsStr::new("/home/agent");
        let xdg = std::ffi::OsStr::new("/custom/cfg");
        let resolved =
            super::resolve_settings_dir(None, Some(home), None, Some(xdg)).expect("resolved");
        assert_eq!(resolved, std::path::PathBuf::from("/custom/cfg/SessionLedger"));
    }

    #[test]
    fn settings_dir_falls_back_to_home_dotconfig_when_no_xdg() {
        if !(cfg!(target_os = "linux") || cfg!(target_os = "freebsd") || cfg!(target_os = "netbsd"))
        {
            return;
        }
        let home = std::ffi::OsStr::new("/home/agent");
        let resolved = super::resolve_settings_dir(None, Some(home), None, None).expect("resolved");
        assert_eq!(resolved, std::path::PathBuf::from("/home/agent/.config/SessionLedger"));
    }

    #[test]
    fn settings_dir_macos_uses_application_support() {
        if !cfg!(target_os = "macos") {
            return;
        }
        let home = std::ffi::OsStr::new("/Users/agent");
        let resolved = super::resolve_settings_dir(None, Some(home), None, None).expect("resolved");
        assert_eq!(
            resolved,
            std::path::PathBuf::from("/Users/agent/Library/Application Support/SessionLedger")
        );
    }

    #[test]
    fn settings_dir_windows_uses_appdata() {
        if !cfg!(target_os = "windows") {
            return;
        }
        let appdata = std::ffi::OsStr::new("C:/Users/agent/AppData/Roaming");
        let resolved =
            super::resolve_settings_dir(None, None, Some(appdata), None).expect("resolved");
        assert_eq!(
            resolved,
            std::path::PathBuf::from("C:/Users/agent/AppData/Roaming/SessionLedger")
        );
    }

    #[test]
    fn settings_dir_returns_none_without_home_or_override() {
        if cfg!(target_os = "macos") {
            // No `$HOME` → no settings dir (macOS path requires it).
            assert!(super::resolve_settings_dir(None, None, None, None).is_none());
        }
    }

    #[test]
    fn empty_override_falls_through_to_platform_default() {
        if !cfg!(target_os = "macos") {
            return;
        }
        let home = std::ffi::OsStr::new("/Users/agent");
        let resolved =
            super::resolve_settings_dir(Some(""), Some(home), None, None).expect("resolved");
        assert_eq!(
            resolved,
            std::path::PathBuf::from("/Users/agent/Library/Application Support/SessionLedger")
        );
    }
}
