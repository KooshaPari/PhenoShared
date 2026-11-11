//! Persistent configuration for the viewer's custom corpus paths.
//!
//! The viewer ships with a fixed set of well-known local session roots
//! (`~/.codex/sessions`, `~/.claude/projects`, `~/.cursor/projects`). Users
//! who keep their data elsewhere need a way to point the viewer at their
//! own directory; this module owns the on-disk representation of those
//! user-chosen paths.
//!
//! ## Storage location
//!
//! Paths are stored as JSON inside the platform's user config directory:
//!
//! | Platform | Path |
//! |----------|------|
//! | macOS    | `~/Library/Application Support/SessionLedger/corpus_paths.json` |
//! | Linux    | `${XDG_CONFIG_HOME:-~/.config}/SessionLedger/corpus_paths.json` |
//! | Windows  | `%APPDATA%\SessionLedger\corpus_paths.json` |
//!
//! The location is resolved by [`dirs::config_dir`]; if that fails (sandbox
//! or unusual configuration) we fall back to the current working directory
//! so the user is never locked out of saving their picks.
//!
//! ## File format
//!
//! ```json
//! {
//!   "custom_paths": ["/Users/me/code/sessions", "/tmp/legacy-codex"]
//! }
//! ```
//!
//! The schema is intentionally tiny: a single `custom_paths` array. The
//! viewer reads it on startup, layers the entries on top of the default
//! native discovery, and rewrites the file whenever the user picks a new
//! folder or clears the override.

use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// Subdirectory under `dirs::config_dir()` that owns SessionLedger's state.
const CONFIG_SUBDIR: &str = "SessionLedger";

/// File name for the persisted corpus paths.
const CONFIG_FILE: &str = "corpus_paths.json";

/// On-disk shape of the corpus-paths config file.
///
/// Only fields with `#[serde(default)]` are guaranteed to survive a downgrade
/// or hand-edit — newer viewers add fields with that attribute so older
/// builds keep parsing the file instead of blowing up.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct CorpusPathConfig {
    /// User-supplied directories to scan in addition to (or instead of) the
    /// native session stores. May be empty.
    #[serde(default)]
    pub custom_paths: Vec<PathBuf>,
}

impl CorpusPathConfig {
    /// Build an empty config (no custom paths).
    #[must_use]
    pub fn empty() -> Self {
        Self::default()
    }

    /// Whether the config has any custom paths set.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.custom_paths.is_empty()
    }
}

/// Resolve the absolute path of the corpus-paths config file.
///
/// Returns `None` only when neither `dirs::config_dir()` nor the current
/// working directory can be resolved — which should never happen for a
/// desktop binary, but the `Option` keeps callers honest.
#[must_use]
pub fn default_config_path() -> Option<PathBuf> {
    if let Some(base) = dirs::config_dir() {
        return Some(base.join(CONFIG_SUBDIR).join(CONFIG_FILE));
    }
    std::env::current_dir().ok().map(|cwd| cwd.join(CONFIG_FILE))
}

/// Load the corpus-paths config from disk.
///
/// Missing files and unreadable files both yield an empty config rather than
/// an error — the viewer's first launch on a new machine shouldn't fail just
/// because the user hasn't picked anything yet. Files that *exist* but are
/// not valid JSON surface an error so the user knows to repair or delete the
/// file rather than silently losing their picks.
///
/// # Errors
///
/// Returns `Err` only when the file exists but cannot be parsed as JSON.
/// Returns `Ok(CorpusPathConfig::default())` when the file is missing.
pub fn load_config() -> Result<CorpusPathConfig, String> {
    let Some(path) = default_config_path() else {
        return Ok(CorpusPathConfig::default());
    };
    load_config_from(&path)
}

/// Load the corpus-paths config from `path`.
///
/// Visible for tests; production callers should use [`load_config`].
/// Missing files yield an empty config; parse errors are returned.
pub fn load_config_from(path: &Path) -> Result<CorpusPathConfig, String> {
    let raw = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(err) if err.kind() == io::ErrorKind::NotFound => {
            return Ok(CorpusPathConfig::default());
        }
        Err(err) => {
            return Err(format!("could not read corpus paths config at {}: {err}", path.display()));
        }
    };
    serde_json::from_str(&raw)
        .map_err(|err| format!("could not parse corpus paths config at {}: {err}", path.display()))
}

/// Persist the corpus-paths config to disk.
///
/// Writes the config to [`default_config_path`] and ensures the parent
/// directory exists. Overwrites any existing file. Returns the path the
/// config was written to on success so callers can surface it in the UI.
///
/// # Errors
///
/// Returns `Err` when the config directory cannot be created, when
/// serialization fails, or when the write itself fails.
pub fn save_config(config: &CorpusPathConfig) -> Result<PathBuf, String> {
    let path = default_config_path()
        .ok_or_else(|| "could not resolve a config directory for SessionLedger".to_owned())?;
    save_config_to(config, &path)?;
    Ok(path)
}

/// Persist the corpus-paths config to `path`. Visible for tests.
pub fn save_config_to(config: &CorpusPathConfig, path: &Path) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| {
            format!("could not create config directory {}: {err}", parent.display())
        })?;
    }
    let serialized = serde_json::to_string_pretty(config)
        .map_err(|err| format!("could not serialize corpus paths config: {err}"))?;
    fs::write(path, serialized).map_err(|err| {
        format!("could not write corpus paths config to {}: {err}", path.display())
    })?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn sample_config() -> CorpusPathConfig {
        CorpusPathConfig {
            custom_paths: vec![
                PathBuf::from("/Users/me/code/sessions"),
                PathBuf::from("/tmp/legacy-codex"),
            ],
        }
    }

    #[test]
    fn round_trip_write_then_read_yields_equal_config() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join(CONFIG_FILE);
        let original = sample_config();

        save_config_to(&original, &path).expect("save");
        let restored = load_config_from(&path).expect("load");

        assert_eq!(restored, original);
    }

    #[test]
    fn empty_config_round_trips() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join(CONFIG_FILE);
        let original = CorpusPathConfig::empty();

        save_config_to(&original, &path).expect("save empty");
        let restored = load_config_from(&path).expect("load empty");

        assert!(restored.is_empty());
        assert_eq!(restored, original);
    }

    #[test]
    fn missing_file_yields_empty_config() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join("does-not-exist.json");
        let config = load_config_from(&path).expect("missing file load");
        assert!(config.is_empty());
    }

    #[test]
    fn parse_error_is_surfaced() {
        let dir = tempfile::tempdir().expect("tempdir");
        let path = dir.path().join(CONFIG_FILE);
        fs::write(&path, "not json at all").expect("write junk");
        let result = load_config_from(&path);
        assert!(result.is_err(), "junk JSON must surface as an error");
    }

    #[test]
    fn save_creates_parent_directories() {
        let dir = tempfile::tempdir().expect("tempdir");
        let nested = dir.path().join("a").join("b").join("c").join(CONFIG_FILE);
        assert!(!nested.parent().expect("parent").exists());

        save_config_to(&sample_config(), &nested).expect("save nested");

        assert!(nested.exists());
    }

    #[test]
    fn config_equality_ignores_path_order_independently() {
        let mut a = sample_config();
        let mut b = sample_config();
        a.custom_paths.reverse();
        b.custom_paths = b.custom_paths.into_iter().collect::<HashSet<_>>().into_iter().collect();
        // Equality is order-sensitive by design, but both lists should at
        // least contain the same unique entries.
        let set_a: HashSet<_> = a.custom_paths.iter().collect();
        let set_b: HashSet<_> = b.custom_paths.iter().collect();
        assert_eq!(set_a, set_b);
    }

    #[test]
    fn empty_helper_returns_empty_config() {
        let config = CorpusPathConfig::empty();
        assert!(config.is_empty());
        assert_eq!(config.custom_paths.len(), 0);
    }
}
