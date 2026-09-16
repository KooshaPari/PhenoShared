//! Shell (Unix `.zshrc` / `.bashrc`) installer generation.
//!
//! Contains helpers for appending `PATH` export lines to the user's shell rc
//! files so that the `phinbox` binaries are available on every new shell.

use std::fs;
use std::io;
use std::path::{Path, PathBuf};

/// Append a `PATH` export line to each existing (or `.zshrc`) shell rc file.
pub(crate) fn update_path_and_rc(bin_dir: &Path) -> Option<Vec<PathBuf>> {
    let mut updated = Vec::new();
    #[cfg(unix)]
    {
        for rc_name in [".zshrc", ".bashrc"] {
            if let Some(home) = home_dir() {
                let rc = home.join(rc_name);
                if rc.exists() || rc_name == ".zshrc" {
                    if let Ok(()) = ensure_path_line(&rc, bin_dir) {
                        updated.push(rc);
                    }
                }
            }
        }
    }
    #[cfg(windows)]
    {
        if let Ok(current) = std::env::var("PATH") {
            let bin_str = bin_dir.display().to_string();
            if !current.split(';').any(|p| p.eq_ignore_ascii_case(&bin_str)) {
                let new_path = format!("{current};{bin_str}");
                let status = std::process::Command::new("setx")
                    .args(["PATH", &new_path])
                    .status();
                match status {
                    Ok(s) if s.success() => updated.push(bin_dir.to_path_buf()),
                    Ok(s) => eprintln!("setx exited with status {s}"),
                    Err(e) => eprintln!("failed to invoke setx: {e}"),
                }
            }
        }
    }
    if updated.is_empty() { None } else { Some(updated) }
}

/// Ensure that the `export PATH` line exists in `rc`.
#[cfg(unix)]
pub(crate) fn ensure_path_line(rc: &Path, bin_dir: &Path) -> io::Result<()> {
    let bin_str = bin_dir.to_string_lossy().to_string();
    let sentinel = format!("export PATH=\"$PATH:{bin_str}\"");
    let existing = fs::read_to_string(rc).unwrap_or_default();
    if existing.lines().any(|line| line.trim() == sentinel) {
        return Ok(());
    }
    let mut file = fs::OpenOptions::new().append(true).create(true).open(rc)?;
    use io::Write;
    writeln!(file, "\n# Added by `phinbox install`")?;
    writeln!(file, "{sentinel}")?;
    Ok(())
}

pub(crate) fn home_dir() -> Option<PathBuf> {
    std::env::var_os("HOME").map(PathBuf::from)
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn install_autostart(cli_path: &Path) -> Result<PathBuf, String> {
    #[cfg(target_os = "macos")]
    {
        let home = home_dir().ok_or_else(|| "HOME not set".to_string())?;
        let agents = home.join("Library").join("LaunchAgents");
        fs::create_dir_all(&agents).map_err(|e| e.to_string())?;
        let plist = agents.join("com.phenotype.phinbox.plist");
        let xml = format!(
            r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.phenotype.phinbox</string>
  <key>ProgramArguments</key>
  <array>
    <string>{}</string>
    <string>daemon</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{}/Library/Logs/phinbox.out</string>
  <key>StandardErrorPath</key><string>{}/Library/Logs/phinbox.err</string>
</dict>
</plist>
"#,
            cli_path.display(),
            home.display(),
            home.display(),
        );
        fs::write(&plist, xml).map_err(|e| e.to_string())?;
        Ok(plist)
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        let home = home_dir().ok_or_else(|| "HOME not set".to_string())?;
        let dir = home.join(".config").join("systemd").join("user");
        fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
        let unit = dir.join("phinbox.service");
        let body = format!(
            "[Unit]\nDescription=Phinbox inbox daemon\nAfter=network.target\n\n\
             [Service]\nExecStart={} daemon\nRestart=on-failure\n\n\
             [Install]\nWantedBy=default.target\n",
            cli_path.display()
        );
        fs::write(&unit, body).map_err(|e| e.to_string())?;
        let _ = std::process::Command::new("systemctl")
            .args(["--user", "enable", "--now", "phinbox.service"])
            .status();
        return Ok(unit);
    }
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn remove_autostart(removed: &mut Vec<String>, warnings: &mut Vec<String>) {
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = home_dir() {
            let plist = home.join("Library").join("LaunchAgents").join("com.phenotype.phinbox.plist");
            if plist.exists() {
                let _ = std::process::Command::new("launchctl").args(["unload", &plist.display().to_string()]).status();
                if let Err(e) = fs::remove_file(&plist) {
                    warnings.push(format!("remove {}: {e}", plist.display()));
                } else {
                    removed.push(plist.display().to_string());
                }
            }
        }
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        if let Some(home) = home_dir() {
            let unit = home.join(".config").join("systemd").join("user").join("phinbox.service");
            if unit.exists() {
                let _ = std::process::Command::new("systemctl").args(["--user", "disable", "--now", "phinbox.service"]).status();
                if let Err(e) = fs::remove_file(&unit) {
                    warnings.push(format!("remove {}: {e}", unit.display()));
                } else {
                    removed.push(unit.display().to_string());
                }
            }
        }
    }
}
