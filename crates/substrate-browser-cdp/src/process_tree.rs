//! Whole-process-tree termination for a launched browser.
//!
//! Chrome is not one process. The parent supervises renderer, GPU, utility and
//! crashpad children. Killing only the parent (what `Child::kill` does) leaves
//! those children alive and reparented to init, which is exactly the leak that
//! let `broker_release` report "browser closed" while a renderer kept running
//! against a throwaway profile.
//!
//! So the launcher puts Chrome in its own process group and this module
//! terminates *the group*. Everything here is scoped twice over: signals go to
//! the group id the launch created, and the final check matches the launch's
//! own unique `--user-data-dir`. A user's real browsers are never signalled:
//! they live in a different group and a different profile directory.

use std::{path::Path, time::Duration};

use crate::{CdpError, Result};

/// How long the group gets to exit after `SIGTERM` before `SIGKILL`.
const TERM_GRACE: Duration = Duration::from_millis(1_000);

/// How long the group gets to exit after `SIGKILL`.
const KILL_GRACE: Duration = Duration::from_secs(3);

/// Poll interval while waiting for a group to disappear.
const POLL_INTERVAL: Duration = Duration::from_millis(50);

/// Send `signal` to every process in `pgid`.
///
/// The negative pid is POSIX's "the whole process group" form. Only the group
/// this launch created is ever addressed.
#[cfg(unix)]
pub(crate) fn signal_group(pgid: u32, signal: i32) -> std::io::Result<()> {
    let pid = libc::pid_t::try_from(pgid)
        .map_err(|_| std::io::Error::from(std::io::ErrorKind::InvalidInput))?;
    // SAFETY: `kill` is a plain syscall with no memory-safety contract; a
    // negative pid addresses the process group rather than a single process.
    if unsafe { libc::kill(-pid, signal) } == 0 {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}

/// Whether any process is still a member of `pgid`.
///
/// `kill(-pgid, 0)` performs POSIX existence checking without delivering a
/// signal. `EPERM` still means "something is there".
#[cfg(unix)]
pub(crate) fn group_exists(pgid: u32) -> bool {
    let Ok(pid) = libc::pid_t::try_from(pgid) else {
        return false;
    };
    // SAFETY: signal 0 delivers nothing; it only reports group membership.
    if unsafe { libc::kill(-pid, 0) } == 0 {
        return true;
    }
    std::io::Error::last_os_error().raw_os_error() == Some(libc::EPERM)
}

/// Pids whose command line still references `user_data_dir`.
///
/// This is the measurement that proves the tree is gone. It matches the
/// launch's own *unique* profile path, never a browser binary name, so the
/// user's real browsers cannot be mistaken for a leftover of this launch.
#[cfg(unix)]
pub fn processes_using_user_data_dir(user_data_dir: &Path) -> Vec<u32> {
    let needle = user_data_dir.to_string_lossy().into_owned();
    if needle.trim().is_empty() {
        return Vec::new();
    }
    // `-ww` disables width truncation so a long `--user-data-dir` is still
    // visible; `pid=,args=` keeps the output machine-readable on macOS and
    // Linux alike.
    let Ok(output) = std::process::Command::new("ps")
        .args(["-ww", "-eo", "pid=,args="])
        .output()
    else {
        return Vec::new();
    };
    if !output.status.success() {
        return Vec::new();
    }

    let mut pids = Vec::new();
    for line in String::from_utf8_lossy(&output.stdout).lines() {
        let line = line.trim_start();
        let Some((pid, command)) = line.split_once(char::is_whitespace) else {
            continue;
        };
        let Ok(pid) = pid.parse::<u32>() else {
            continue;
        };
        if references_path(command, &needle) {
            pids.push(pid);
        }
    }
    pids
}

/// Whether `command` contains `path` as a whole argv token.
///
/// Plain substring matching would let `/tmp/profile` match
/// `/tmp/profile-2`, which is a *different* launch. Requiring end-of-token
/// after every occurrence keeps the match scoped to this launch's directory.
#[cfg(unix)]
fn references_path(command: &str, path: &str) -> bool {
    let mut rest = command;
    while let Some(index) = rest.find(path) {
        let after = &rest[index + path.len()..];
        if after.is_empty() || after.starts_with(char::is_whitespace) {
            return true;
        }
        rest = after;
    }
    false
}

/// Scan the process table off the async runtime.
///
/// `None` means the scan itself failed. That is deliberately distinct from
/// "nothing matched": a failed read must never be reported as a clean shutdown.
#[cfg(unix)]
async fn scan(user_data_dir: &Path) -> Option<Vec<u32>> {
    // `spawn_blocking` needs an owned path, so hand over a copy.
    let dir = user_data_dir.to_path_buf();
    tokio::task::spawn_blocking(move || processes_using_user_data_dir(&dir))
        .await
        .ok()
}

/// Wait until the group is gone *and* no process references the profile.
#[cfg(unix)]
async fn wait_gone(pgid: u32, user_data_dir: &Path, budget: Duration) -> bool {
    let deadline = tokio::time::Instant::now() + budget;
    loop {
        // Group membership is a cheap syscall; only pay for a process-table
        // scan once the group is gone, to catch a child that escaped it.
        if !group_exists(pgid) && matches!(scan(user_data_dir).await.as_deref(), Some([])) {
            return true;
        }
        if tokio::time::Instant::now() >= deadline {
            return false;
        }
        tokio::time::sleep(POLL_INTERVAL).await;
    }
}

/// Terminate the whole process group `pgid`, then prove it is gone.
///
/// Escalation is bounded and measured:
/// 1. `SIGTERM` the group (graceful-ish), bounded wait.
/// 2. `SIGKILL` the group, bounded wait.
/// 3. `SIGKILL` any straggler that escaped the group but still holds this
///    launch's unique throwaway profile directory, bounded wait.
///
/// Returns `Err(CdpError::Timeout)` naming the survivors if anything is still
/// alive after all three steps, so callers never report a closed browser that
/// is still running.
#[cfg(unix)]
pub(crate) async fn terminate_group(pgid: u32, user_data_dir: &Path) -> Result<()> {
    let _ = signal_group(pgid, libc::SIGTERM);
    if wait_gone(pgid, user_data_dir, TERM_GRACE).await {
        return Ok(());
    }

    let _ = signal_group(pgid, libc::SIGKILL);
    if wait_gone(pgid, user_data_dir, KILL_GRACE).await {
        return Ok(());
    }

    for _ in 0..20 {
        let Some(survivors) = scan(user_data_dir).await else {
            break;
        };
        if survivors.is_empty() {
            return Ok(());
        }
        for pid in &survivors {
            if let Ok(pid) = libc::pid_t::try_from(*pid) {
                // SAFETY: plain syscall; the pid was matched to this launch's
                // own profile directory, and nothing else is signalled.
                unsafe {
                    libc::kill(pid, libc::SIGKILL);
                }
            }
        }
        tokio::time::sleep(POLL_INTERVAL).await;
    }

    match scan(user_data_dir).await {
        Some(survivors) if survivors.is_empty() => Ok(()),
        Some(survivors) => Err(CdpError::Timeout(format!(
            "browser process group {pgid} survived shutdown; still running with {}: {:?}",
            user_data_dir.display(),
            survivors
        ))),
        None => Err(CdpError::Timeout(format!(
            "could not verify that {pgid} is gone: the process table could not be read",
        ))),
    }
}
