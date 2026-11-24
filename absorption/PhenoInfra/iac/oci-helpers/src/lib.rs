//! `oci-helpers` — shared utilities extracted from oci-lottery and
//! oci-post-acquire to avoid duplication across the `iac/` workspace.
//!
//! Per the DAG unit B14 mandate, this crate serves as the canonical home
//! for path helpers, OCI CLI wrappers, and other common patterns that
//! were previously copy-pasted between sibling crates.

use std::path::PathBuf;

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------

/// Resolve `~` prefix to `$HOME`. If the path does not start with `~/`,
/// returns it unchanged.
pub fn expand_home(p: &str) -> PathBuf {
    if let Some(rest) = p.strip_prefix("~/") {
        if let Some(home) = home_dir() {
            return home.join(rest);
        }
    }
    PathBuf::from(p)
}

/// Return `$HOME` as a `PathBuf`, or `None` if unset.
pub fn home_dir() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

/// Convenience wrapper: returns `$HOME` or a fallback (default `/tmp`).
pub fn home_or_fallback() -> PathBuf {
    home_dir().unwrap_or_else(|| PathBuf::from("/tmp"))
}

// ---------------------------------------------------------------------------
// File I/O helpers
// ---------------------------------------------------------------------------

/// Idempotent JSON load: reads and deserializes a JSON file at `path`.
/// If the file does not exist, returns `Ok(default)`.
pub async fn load_json_or<T>(path: &PathBuf, default: T) -> anyhow::Result<T>
where
    T: serde::de::DeserializeOwned,
{
    if tokio::fs::try_exists(path).await.unwrap_or(false) {
        let raw = tokio::fs::read_to_string(path).await?;
        Ok(serde_json::from_str(&raw)?)
    } else {
        Ok(default)
    }
}

/// Idempotent JSON save: writes `value` as pretty-printed JSON to `path`,
/// creating parent directories as needed.
pub async fn save_json<T>(path: &PathBuf, value: &T) -> anyhow::Result<()>
where
    T: serde::Serialize,
{
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let raw = serde_json::to_string_pretty(value)?;
    tokio::fs::write(path, raw).await?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Process helpers
// ---------------------------------------------------------------------------

/// Check whether a binary is on `$PATH` by invoking `command -v` via the
/// shell. Respects shell functions, aliases, and per-shell PATH munging.
pub async fn which_on_path(bin: &str) -> bool {
    tokio::process::Command::new("sh")
        .arg("-c")
        .arg(format!("command -v {bin} >/dev/null 2>&1"))
        .status()
        .await
        .map(|s| s.success())
        .unwrap_or(false)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_home_or_fallback() {
        let h = home_or_fallback();
        assert!(h.is_absolute());
    }
}
