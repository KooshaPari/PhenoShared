//! Native tray notification logic (macOS, Windows, Linux).
//!
//! Each platform dispatches to a native mechanism:
//! - macOS: `osascript` Notification Center
//! - Windows: PowerShell `NotifyIcon` balloon
//! - Linux: `notify-send`

use super::{escape_applescript, escape_powershell, truncate, NotifyAttempt};
use crate::inbox::{NotificationKind, PendingRequest};

/// Fire a platform-native notification.
#[must_use]
pub fn notify_native(req: &PendingRequest) -> NotifyAttempt {
    let result = match crate::platform() {
        crate::Platform::Macos => notify_native_macos(req),
        crate::Platform::Windows => notify_native_windows(req),
        crate::Platform::Linux => notify_native_linux(req),
        crate::Platform::Unknown => Err("no native notifier known for this platform".into()),
    };
    match result {
        Ok(msg) => NotifyAttempt::ok(NotificationKind::NativeNotification, msg),
        Err(e) => NotifyAttempt::err(NotificationKind::NativeNotification, e),
    }
}

fn notify_native_macos(req: &PendingRequest) -> Result<String, String> {
    let script = format!(
        "display notification \"{}\" with title \"{}\" subtitle \"\"",
        escape_applescript(&truncate(&req.spec.question, 200)),
        escape_applescript(&truncate(&req.spec.title, 60)),
    );
    super::run_osascript(&script).map(|()| "ok".into())
}

fn notify_native_windows(req: &PendingRequest) -> Result<String, String> {
    use std::process::Command;
    let title = escape_powershell(&truncate(&req.spec.title, 60));
    let question = escape_powershell(&truncate(&req.spec.question, 200));
    let ps = format!(
        "Add-Type -AssemblyName System.Windows.Forms | Out-Null;\n\
         $n = New-Object System.Windows.Forms.NotifyIcon;\n\
         $n.Icon = [System.Drawing.SystemIcons]::Information;\n\
         $n.BalloonTipIcon = 'Info';\n\
         $n.Visible = $true;\n\
         $n.ShowBalloonTip(10000, '{title}', '{question}', [System.Windows.Forms.ToolTipIcon]::Info);\n\
         Start-Sleep -Seconds 6;\n\
         $n.Dispose();"
    );
    let status = Command::new("powershell")
        .args(["-NoProfile", "-Command", &ps])
        .status()
        .map_err(|e| format!("spawn powershell: {e}"))?;
    if status.success() {
        Ok("ok".into())
    } else {
        Err(format!("powershell exit {status:?}"))
    }
}

fn notify_native_linux(req: &PendingRequest) -> Result<String, String> {
    use std::process::Command;
    let title = truncate(&req.spec.title, 60);
    let body = truncate(&req.spec.question, 200);
    let status = Command::new("notify-send")
        .args(["-u", "normal", &title, &body])
        .status()
        .map_err(|e| format!("spawn notify-send: {e}"))?;
    if status.success() {
        Ok("ok".into())
    } else {
        Err(format!("notify-send exit {status:?}"))
    }
}
