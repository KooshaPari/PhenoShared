//! Process liveness and process-instance identity.
//!
//! A pid on its own is not an identity: the kernel recycles pids, so a pid
//! recorded yesterday can name an unrelated process today. Anything that asks
//! "is the *same* process still there?" must bind the pid to a start-time
//! identity via [`process_start_identity`] and compare the two.
//!
//! Both helpers are conservative: when a question cannot be answered they
//! report the process as alive / unidentifiable, so a caller never reaps state
//! on a guess.

/// Whether `pid` names a live process.
///
/// `kill(pid, 0)` performs the permission and existence checks without sending a
/// signal: it returns 0 when the process exists, and EPERM when it exists but is
/// owned by another user. Only ESRCH means gone.
#[cfg(unix)]
pub(crate) fn pid_is_alive(pid: u32) -> bool {
    // SAFETY: signal 0 sends nothing; it only performs the existence check.
    let rc = unsafe { libc::kill(pid as i32, 0) };
    if rc == 0 {
        return true;
    }
    std::io::Error::last_os_error().raw_os_error() == Some(libc::EPERM)
}

/// No portable liveness check here, so assume alive: never reap on a guess.
#[cfg(not(unix))]
pub(crate) fn pid_is_alive(_pid: u32) -> bool {
    true
}

/// A stable, comparable identity for the process *instance* currently running
/// as `pid`, or `None` when the platform cannot supply one.
///
/// The value is only ever compared for equality: it is opaque, platform-tagged,
/// and meaningless across boots. It is inexpensive - on Linux it is one small
/// file read and spawns nothing; on macOS it shells out to `ps -o lstart=`.
pub(crate) fn process_start_identity(pid: u32) -> Option<String> {
    if pid == 0 {
        return None;
    }
    read_start_identity(pid)
}

/// Linux: field 22 of `/proc/<pid>/stat`, the start time in clock ticks since
/// boot. Paired with the pid, that is unique for the life of a boot.
#[cfg(target_os = "linux")]
fn read_start_identity(pid: u32) -> Option<String> {
    let stat = std::fs::read_to_string(format!("/proc/{pid}/stat")).ok()?;
    // Field 2 is `(comm)` and may itself contain spaces or parentheses, so
    // split after the LAST ')': the remainder begins at field 3 (state). Field
    // 22 is therefore index 19 of that tail.
    let tail = &stat[stat.rfind(')')? + 1..];
    let starttime = tail.split_whitespace().nth(19)?;
    Some(format!("linux-starttime:{starttime}"))
}

/// macOS: the wall-clock start time as printed by `ps -o lstart=`.
#[cfg(target_os = "macos")]
fn read_start_identity(pid: u32) -> Option<String> {
    let output = std::process::Command::new("ps")
        .args(["-o", "lstart=", "-p", &pid.to_string()])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let started = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if started.is_empty() {
        None
    } else {
        Some(format!("macos-lstart:{started}"))
    }
}

/// Any other target: no cheap, reliable start-time identity, so report none and
/// let callers fall back to pid-only liveness.
#[cfg(not(any(target_os = "linux", target_os = "macos")))]
fn read_start_identity(_pid: u32) -> Option<String> {
    None
}
