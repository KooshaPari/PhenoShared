//! PowerShell / Windows installer generation.
use std::path::{Path, PathBuf};


#[allow(dead_code)]
pub(crate) fn update_path_via_setx(bin_dir: &Path) -> Option<PathBuf> {
    #[cfg(windows)]
    {
        if let Ok(current) = std::env::var("PATH") {
            let bin_str = bin_dir.display().to_string();
            if !current.split(';').any(|p| p.eq_ignore_ascii_case(&bin_str)) {
                let new_path = format!("{current};{bin_str}");
                let status = Command::new("setx").args(["PATH", &new_path]).status();
                return match status {
                    Ok(s) if s.success() => Some(bin_dir.to_path_buf()),
                    Ok(s) => { eprintln!("setx exited with status {s}"); None }
                    Err(e) => { eprintln!("failed to invoke setx: {e}"); None }
                };
            }
        }
    }
    #[cfg(not(windows))]
    { let _ = bin_dir; }
    None
}

#[allow(dead_code)]
pub(crate) fn install_scheduled_task(cli_path: &Path) -> Result<PathBuf, String> {
    #[cfg(target_os = "windows")]
    {
        let status = Command::new("schtasks")
            .args(["/Create", "/TN", "PhinboxDaemon", "/TR",
                   &format!("\"{}\" daemon", cli_path.display()),
                   "/SC", "ONLOGON", "/RL", "LIMITED", "/F"])
            .status().map_err(|e| e.to_string())?;
        if !status.success() { return Err(format!("schtasks failed with status {status}")); }
        Ok(PathBuf::from(r"C:\Windows\System32\Tasks\PhinboxDaemon"))
    }
    #[cfg(not(target_os = "windows"))]
    { let _ = cli_path; Err("scheduled tasks are only available on Windows".into()) }
}

#[allow(dead_code)]
pub(crate) fn remove_scheduled_task() {
    #[cfg(target_os = "windows")]
    { let _ = Command::new("schtasks").args(["/Delete", "/TN", "PhinboxDaemon", "/F"]).status(); }
}
