//! Install the bundled Ghostty shader pack into the user's config dir.
//!
//! Shaders are compiled into the binary via `include_str!` so a published
//! `rck` binary is self-contained. `install` copies the requested shader into
//! `~/.config/ghostty/shaders/<name>.glsl` and prints the config snippet the
//! user needs to add.

use anyhow::{anyhow, Context, Result};
use std::path::{Path, PathBuf};

/// Bundled shaders, keyed by name.
pub fn bundled(name: &str) -> Option<&'static str> {
    match name {
        "focus-vignette" => Some(include_str!("../../../shaders/focus-vignette.glsl")),
        "progress-pulse" => Some(include_str!("../../../shaders/progress-pulse.glsl")),
        "agent-active" => Some(include_str!("../../../shaders/agent-active.glsl")),
        _ => None,
    }
}

/// Names of all bundled shaders.
pub fn list() -> &'static [&'static str] {
    &["focus-vignette", "progress-pulse", "agent-active"]
}

/// Default install directory: `$XDG_CONFIG_HOME/ghostty/shaders` or
/// `~/.config/ghostty/shaders`.
pub fn default_install_dir() -> Result<PathBuf> {
    if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
        return Ok(PathBuf::from(xdg).join("ghostty").join("shaders"));
    }
    let home = std::env::var("HOME").map_err(|_| anyhow!("HOME env var not set"))?;
    Ok(PathBuf::from(home)
        .join(".config")
        .join("ghostty")
        .join("shaders"))
}

/// Install the shader `name` into `dir` (falls back to [`default_install_dir`]
/// when `None`). Returns the full path written.
pub fn install(name: &str, dir: Option<&Path>) -> Result<PathBuf> {
    let contents =
        bundled(name).ok_or_else(|| anyhow!("unknown shader: {name}. known: {:?}", list()))?;
    let dir = match dir {
        Some(d) => d.to_path_buf(),
        None => default_install_dir()?,
    };
    std::fs::create_dir_all(&dir).with_context(|| format!("creating {}", dir.display()))?;
    let dest = dir.join(format!("{name}.glsl"));
    std::fs::write(&dest, contents).with_context(|| format!("writing {}", dest.display()))?;
    Ok(dest)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bundled_lookup_works() {
        assert!(bundled("focus-vignette").is_some());
        assert!(bundled("nonexistent").is_none());
    }

    #[test]
    fn install_writes_file() {
        let tmp = std::env::temp_dir().join(format!("rck-shader-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&tmp);
        let path = install("focus-vignette", Some(&tmp)).unwrap();
        assert!(path.exists());
        let content = std::fs::read_to_string(&path).unwrap();
        assert!(content.contains("iFocus") || content.contains("void main"));
        let _ = std::fs::remove_dir_all(&tmp);
    }

    #[test]
    fn install_unknown_errors() {
        assert!(install("nope", None).is_err());
    }
}
