//! `phinbox install` -- copy binaries into a prefix dir (default
//! `~/.local/bin`), register the inbox daemon with the platform launcher, and
//! run a smoke test.  Idempotent; re-running refreshes binaries in place.
//!
//! - **macOS**: `LaunchAgent` plist in `~/Library/LaunchAgents`
//! - **Windows**: `schtasks` scheduled task + `setx` PATH
//! - **Linux**: systemd user unit in `~/.config/systemd/user`

mod powershell;
mod shell;

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, serde::Serialize)]
pub struct InstallReport {
    pub bin_dir: PathBuf,
    pub cli_path: PathBuf,
    pub mcp_path: PathBuf,
    pub inbox_dir: PathBuf,
    pub path_exports: Vec<PathBuf>,
    pub shell_rc_updated: Vec<PathBuf>,
    pub autostart_installed: bool,
    pub autostart_target: Option<PathBuf>,
    pub smoke: Option<SmokeResult>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct SmokeResult {
    pub ok: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: Option<i32>,
}

#[derive(Debug, Clone)]
pub struct InstallOptions {
    pub prefix: Option<PathBuf>,
    pub inbox_dir: PathBuf,
    pub register_launch_agent: bool,
    pub dry_run: bool,
    pub update_shell_rc: bool,
}

impl Default for InstallOptions {
    fn default() -> Self {
        Self {
            prefix: None,
            inbox_dir: default_inbox_root(),
            register_launch_agent: true,
            dry_run: false,
            update_shell_rc: false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct UninstallOptions {
    pub prefix: Option<PathBuf>,
    pub inbox_dir: PathBuf,
    pub assume_yes: bool,
}

impl Default for UninstallOptions {
    fn default() -> Self {
        Self {
            prefix: None,
            inbox_dir: default_inbox_root(),
            assume_yes: false,
        }
    }
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct UninstallReport {
    pub removed: Vec<String>,
    pub warnings: Vec<String>,
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

#[must_use]
pub fn default_bin_dir() -> PathBuf {
    if let Ok(p) = std::env::var("PHINBOX_BIN") {
        return PathBuf::from(p);
    }
    if cfg!(windows) {
        if let Ok(local) = std::env::var("LOCALAPPDATA") {
            return PathBuf::from(local).join("phinbox").join("bin");
        }
        return PathBuf::from(r"C:\Program Files\phinbox\bin");
    }
    if let Ok(home) = std::env::var("HOME") {
        return PathBuf::from(home).join(".local").join("bin");
    }
    PathBuf::from("/usr/local/bin")
}

fn default_inbox_root() -> PathBuf {
    if let Ok(p) = std::env::var("PHINBOX_INBOX_DIR") { return PathBuf::from(p); }
    if let Ok(p) = std::env::var("XDG_DATA_HOME") { return PathBuf::from(p).join("phinbox"); }
    if cfg!(target_os = "macos") {
        if let Some(home) = std::env::var_os("HOME") {
            return PathBuf::from(home).join("Library/Application Support/phinbox");
        }
    }
    if cfg!(target_os = "windows") {
        if let Ok(p) = std::env::var("LOCALAPPDATA") { return PathBuf::from(p).join("phinbox"); }
    }
    if let Some(home) = std::env::var_os("HOME") { return PathBuf::from(home).join(".local/share/phinbox"); }
    std::env::temp_dir().join("phinbox-inbox")
}

#[must_use]
pub fn source_bin_dir() -> PathBuf {
    if let Ok(p) = std::env::var("PHINBOX_SRC_BIN") {
        let p = PathBuf::from(p);
        if p.is_dir() { return p; }
    }
    std::env::current_exe().ok()
        .and_then(|p| p.parent().map(std::path::Path::to_path_buf))
        .unwrap_or_else(|| PathBuf::from("."))
}

fn copy_binary(src: &Path, dst_dir: &Path, name: &str) -> Result<PathBuf, String> {
    let exe = if cfg!(windows) { format!("{name}.exe") } else { name.to_string() };
    let src_path = src.join(&exe);
    let dst_path = dst_dir.join(&exe);
    if !src_path.exists() {
        return Err(format!("source binary not found: {} (build phinbox first or set $PHINBOX_SRC_BIN)", src_path.display()));
    }
    fs::copy(&src_path, &dst_path)
        .map_err(|e| format!("copy {} -> {}: {}", src_path.display(), dst_path.display(), e))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = fs::metadata(&dst_path) {
            let mut perm = meta.permissions();
            perm.set_mode(0o755);
            let _ = fs::set_permissions(&dst_path, perm);
        }
    }
    Ok(dst_path)
}

fn run_smoke(cli: &Path) -> Result<SmokeResult, String> {
    let output = Command::new(cli).args(["smoke", "--no-render"]).output()
        .map_err(|e| format!("failed to spawn smoke: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    Ok(SmokeResult { ok: output.status.success(), stdout, stderr, exit_code: output.status.code() })
}

// ---------------------------------------------------------------------------
// Orchestration
// ---------------------------------------------------------------------------

pub fn install(opts: &InstallOptions) -> Result<InstallReport, String> {
    let bin_dir = opts.prefix.clone().unwrap_or_else(default_bin_dir);
    let mut report = InstallReport {
        bin_dir: bin_dir.clone(), cli_path: PathBuf::new(), mcp_path: PathBuf::new(),
        inbox_dir: opts.inbox_dir.clone(), path_exports: Vec::new(), shell_rc_updated: Vec::new(),
        autostart_installed: false, autostart_target: None, smoke: None, warnings: Vec::new(),
    };
    if opts.dry_run {
        report.cli_path = bin_dir.join(if cfg!(windows) { "phinbox.exe" } else { "phinbox" });
        report.mcp_path = bin_dir.join(if cfg!(windows) { "phinbox-mcp.exe" } else { "phinbox-mcp" });
        return Ok(report);
    }
    fs::create_dir_all(&bin_dir).map_err(|e| format!("failed to create bin dir {}: {}", bin_dir.display(), e))?;
    fs::create_dir_all(&opts.inbox_dir).ok();
    let src = source_bin_dir();
    report.cli_path = copy_binary(&src, &bin_dir, "phinbox")?;
    report.mcp_path = copy_binary(&src, &bin_dir, "phinbox-mcp")?;
    if opts.update_shell_rc {
        if let Some(rc) = shell::update_path_and_rc(&bin_dir) { report.shell_rc_updated.extend(rc); }
    }
    if opts.register_launch_agent {
        match install_autostart(&report.cli_path) {
            Ok(target) => { report.autostart_installed = true; report.autostart_target = Some(target); }
            Err(e) => report.warnings.push(format!("autostart: {e}")),
        }
    }
    match run_smoke(&report.cli_path) {
        Ok(s) => report.smoke = Some(s),
        Err(e) => report.warnings.push(format!("smoke: {e}")),
    }
    Ok(report)
}

pub fn uninstall(opts: &UninstallOptions) -> Result<UninstallReport, String> {
    let bin_dir = opts.prefix.clone().unwrap_or_else(default_bin_dir);
    let mut removed = Vec::new();
    let mut warnings = Vec::new();
    for name in ["phinbox", "phinbox-mcp"] {
        let exe = if cfg!(windows) { format!("{name}.exe") } else { name.to_string() };
        let p = bin_dir.join(&exe);
        if p.exists() {
            if let Err(e) = fs::remove_file(&p) { warnings.push(format!("remove {}: {e}", p.display())); }
            else { removed.push(p.display().to_string()); }
        }
    }
    #[cfg(not(target_os = "windows"))]
    { shell::remove_autostart(&mut removed, &mut warnings); }
    #[cfg(target_os = "windows")]
    { powershell::remove_scheduled_task(); }
    Ok(UninstallReport { removed, warnings })
}

fn install_autostart(cli_path: &Path) -> Result<PathBuf, String> {
    #[cfg(not(target_os = "windows"))]
    { shell::install_autostart(cli_path) }
    #[cfg(target_os = "windows")]
    { powershell::install_scheduled_task(cli_path) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_bin_dir_is_resolvable() { let _ = default_bin_dir(); }

    #[test]
    fn install_dry_run_does_not_touch_disk() {
        let report = install(&InstallOptions {
            prefix: Some(PathBuf::from("/tmp/phinbox-dry-run-test")),
            dry_run: true, ..Default::default()
        }).unwrap();
        assert!(report.autostart_target.is_none());
        assert!(!report.cli_path.as_os_str().is_empty());
        assert!(!Path::new("/tmp/phinbox-dry-run-test/phinbox").exists());
    }

    #[test]
    fn uninstall_on_missing_is_a_noop() {
        let r = uninstall(&UninstallOptions {
            prefix: Some(PathBuf::from("/tmp/phinbox-missing-for-test")),
            assume_yes: true, ..Default::default()
        }).unwrap();
        assert!(r.removed.is_empty());
    }
}
