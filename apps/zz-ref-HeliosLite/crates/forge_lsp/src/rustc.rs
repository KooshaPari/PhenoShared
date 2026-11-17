//! `cargo check` provider — runs `cargo check --message-format=json` on the
//! file's crate and parses the JSON messages into `Diagnostic` entries.
//!
//! `cargo check` is the cheapest diagnostic path: it type-checks
//! without producing codegen artifacts, so it completes in seconds
//! even on large crates. We invoke it on the closest enclosing
//! `Cargo.toml` (workspace-or-package).

use std::path::{Path, PathBuf};
use std::process::Command;

use serde::Deserialize;

use crate::diagnostic::{Diagnostic, DiagnosticSeverity};
use crate::provider::{DiagnosticsProvider, DiagnosticsResult};

/// One entry from `cargo check --message-format=json` output.
#[derive(Debug, Deserialize)]
struct CargoCompilerMessage {
    message: String,
    #[serde(default)]
    code: Option<CargoCode>,
    #[serde(default)]
    level: Option<String>,
    #[serde(default)]
    spans: Vec<CargoSpan>,
}

#[derive(Debug, Deserialize)]
struct CargoCode {
    code: Option<String>,
}

#[derive(Debug, Deserialize)]
struct CargoSpan {
    file_name: Option<String>,
    line_start: Option<u32>,
    #[serde(default)]
    line_end: Option<u32>,
    #[serde(default)]
    column_start: Option<u32>,
    #[serde(default)]
    column_end: Option<u32>,
    is_primary: Option<bool>,
}

/// `cargo check` provider. Run via [`DiagnosticsService`].
#[derive(Default)]
pub struct RustcProvider;

impl RustcProvider {
    pub const fn new() -> Self {
        Self
    }
}

impl DiagnosticsProvider for RustcProvider {
    fn name(&self) -> &'static str {
        "rustc"
    }

    fn supports(&self, path: &Path) -> bool {
        path.extension()
            .and_then(|e| e.to_str())
            .map(|e| e == "rs")
            .unwrap_or(false)
    }

    fn diagnostics(&self, path: &Path, workspace_root: &Path) -> DiagnosticsResult {
        // Find the closest enclosing Cargo.toml.
        let cargo_root = match find_cargo_root(path, workspace_root) {
            Some(r) => r,
            None => {
                return Err(format!("no Cargo.toml found for {}", path.display()));
            }
        };

        let output = match Command::new("cargo")
            .arg("check")
            .arg("--message-format=json")
            .arg("--quiet")
            .arg("--manifest-path")
            .arg(cargo_root.join("Cargo.toml"))
            .arg("--color=never")
            .current_dir(&cargo_root)
            .output()
        {
            Ok(out) => out,
            Err(e) => {
                return Err(format!("failed to spawn cargo: {e} (is Rust installed?)"));
            }
        };

        let stdout = String::from_utf8(output.stdout.clone()).unwrap_or_else(|e| {
            tracing::warn!("cargo check stdout is not valid UTF-8: {e}");
            String::new()
        });
        let mut diagnostics = Vec::new();
        for line in stdout.lines() {
            if line.is_empty() {
                continue;
            }
            let parsed: CargoCompilerMessage = match serde_json::from_str(line) {
                Ok(m) => m,
                Err(_) => continue,
            };
            if parsed.message.is_empty() {
                continue;
            }
            // Pick the primary span (is_primary=true) for the line/file.
            let span = parsed
                .spans
                .iter()
                .find(|s| s.is_primary.unwrap_or(false))
                .or_else(|| parsed.spans.first());
            let (file, line_num) = match span {
                Some(s) => (
                    PathBuf::from(s.file_name.clone().unwrap_or_default()),
                    s.line_start.unwrap_or(1),
                ),
                None => continue,
            };
            let severity = match parsed.level.as_deref() {
                Some("error") => DiagnosticSeverity::Error,
                Some("warning") => DiagnosticSeverity::Warning,
                Some("note") => DiagnosticSeverity::Information,
                Some("help") => DiagnosticSeverity::Hint,
                _ => DiagnosticSeverity::Warning,
            };
            let mut message = parsed.message.clone();
            if let Some(code) = parsed.code.as_ref().and_then(|c| c.code.clone()) {
                message = format!("{code}: {message}");
            }
            diagnostics.push(Diagnostic::new(file, severity, line_num, message));
        }
        Ok(diagnostics)
    }
}

/// Walk up from `path` looking for the closest `Cargo.toml`. Returns
/// `None` when no manifest exists (no rust diagnostic pass will run).
fn find_cargo_root(path: &Path, workspace_root: &Path) -> Option<PathBuf> {
    let mut start = if path.is_file() {
        path.parent().map(Path::to_path_buf)?
    } else {
        path.to_path_buf()
    };
    loop {
        if start.join("Cargo.toml").is_file() {
            return Some(start);
        }
        if start == workspace_root || start.parent().is_none() {
            return None;
        }
        start = start.parent()?.to_path_buf();
    }
}

#[cfg(test)]
#[allow(unused, missing_docs)]
mod tests {
    use super::*;

    #[test]
    fn rustc_provider_supports_rs_only() {
        let p = RustcProvider::new();
        assert!(p.supports(Path::new("foo.rs")));
        assert!(!p.supports(Path::new("foo.RS")));
        assert!(!p.supports(Path::new("foo.toml")));
        assert!(!p.supports(Path::new("foo")));
    }

    #[test]
    fn rustc_provider_name() {
        assert_eq!(RustcProvider::new().name(), "rustc");
    }

    #[test]
    fn rustc_provider_errors_without_cargo_manifest() {
        let dir = std::env::temp_dir().join("forge_lsp_test_no_cargo");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let r = RustcProvider::new().diagnostics(&dir.join("foo.rs"), &dir);
        assert!(r.is_err(), "no manifest should produce Err");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn rustc_provider_returns_empty_for_unsupported() {
        assert!(!RustcProvider::new().supports(Path::new("foo.txt")));
        assert!(!RustcProvider::new().supports(Path::new("foo.py")));
    }

    #[test]
    fn find_cargo_root_returns_workspace_when_no_manifest() {
        let dir = std::env::temp_dir().join("forge_lsp_test_nomf");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let nested = dir.join("src");
        std::fs::create_dir_all(&nested).unwrap();
        let r = find_cargo_root(&nested.join("foo.rs"), &dir);
        assert!(r.is_none());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn find_cargo_root_returns_manifest_when_present() {
        let dir = std::env::temp_dir().join("forge_lsp_test_mf");
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("Cargo.toml"),
            "[package]\nname=\"x\"\nversion=\"0.0.0\"\nedition=\"2021\"\n",
        )
        .unwrap();
        let nested = dir.join("src");
        std::fs::create_dir_all(&nested).unwrap();
        let r = find_cargo_root(&nested.join("foo.rs"), &dir).unwrap();
        assert_eq!(r, dir);
        let _ = std::fs::remove_dir_all(&dir);
    }
}
