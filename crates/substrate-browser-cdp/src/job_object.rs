//! Whole-process-tree termination for a launched browser on Windows.
//!
//! Windows has no POSIX process group, so `process_tree` cannot apply. The
//! equivalent authority is a **job object**: a kernel object that every
//! descendant inherits automatically at creation. Assigning the spawned Chrome
//! to a fresh job means `TerminateJobObject` reaches the renderer, GPU, utility
//! and crashpad children in one deterministic call, instead of the single
//! `Child::kill` that left them running.
//!
//! Scoping is structural rather than textual. A job created here starts empty,
//! so membership *is* the set of processes this launch created; there is no
//! command line to match and no way for another launch - or the user's own
//! browser - to be a member. `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` is set as a
//! safety net: when the last handle closes (including on a dropped
//! [`crate::ChromeProcess`]) the kernel terminates every remaining member, so a
//! handle that is never shut down explicitly still cannot leak a tree.
//!
//! The `--user-data-dir` path is used only to identify this launch in error
//! messages; it is never a kill criterion on Windows, because asking the kernel
//! "is this pid in *our* job" is both stricter and cheaper than matching argv.

use std::{io, path::Path, time::Duration};

use windows_sys::{
    core::BOOL,
    Win32::{
        Foundation::{CloseHandle, HANDLE, INVALID_HANDLE_VALUE},
        System::{
            Diagnostics::ToolHelp::{
                CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W,
                TH32CS_SNAPPROCESS,
            },
            JobObjects::{
                AssignProcessToJobObject, CreateJobObjectW, IsProcessInJob,
                JobObjectBasicAccountingInformation, JobObjectExtendedLimitInformation,
                QueryInformationJobObject, SetInformationJobObject, TerminateJobObject,
                JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
            },
            Threading::{
                OpenProcess, TerminateProcess, PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_TERMINATE,
            },
        },
    },
};

use crate::{CdpError, Result};

// The budgets mirror `process_tree` (unix) so both platforms make the same
// promise about how long shutdown may take before it is declared failed. They
// are repeated rather than shared because the unix module is deliberately left
// untouched.
/// How long the job gets to empty after the first `TerminateJobObject`.
const TERM_GRACE: Duration = Duration::from_millis(1_000);

/// How long the job gets to empty after the second `TerminateJobObject`.
const KILL_GRACE: Duration = Duration::from_secs(3);

/// Poll interval while waiting for a job to empty.
const POLL_INTERVAL: Duration = Duration::from_millis(50);

/// Owned handle to the job object that owns one launch's process tree.
///
/// The handle is a kernel object reference, valid process-wide and safe to use
/// from any thread; dropping it closes the handle, which - with
/// `KILL_ON_JOB_CLOSE` set - terminates every member still alive.
pub(crate) struct JobHandle(HANDLE);

// SAFETY: Win32 handles are process-wide kernel references, not thread-affine
// memory, and this type holds no interior mutability. It exists only so the
// launcher can move ownership into `ChromeProcess`, which is `Send`.
unsafe impl Send for JobHandle {}
// SAFETY: same reasoning; every method takes `&self` and the underlying calls
// are themselves thread-safe for a valid handle.
unsafe impl Sync for JobHandle {}

impl JobHandle {
    /// Create an unnamed job with `KILL_ON_JOB_CLOSE` armed.
    pub(crate) fn create() -> io::Result<Self> {
        // SAFETY: null attributes and a null name ask for an unnamed job with
        // default security; no pointers are dereferenced by this call.
        let handle = unsafe { CreateJobObjectW(std::ptr::null(), std::ptr::null()) };
        if handle.is_null() || handle == INVALID_HANDLE_VALUE {
            return Err(io::Error::last_os_error());
        }
        let job = Self(handle);
        job.arm_kill_on_close()?;
        Ok(job)
    }

    /// Make the kernel terminate the tree when the last handle closes.
    fn arm_kill_on_close(&self) -> io::Result<()> {
        // Only `KILL_ON_JOB_CLOSE`: no UI restrictions, no memory or CPU
        // limits, so Chrome behaves inside the job exactly as it would outside
        // one. `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` is zero-initialised, which
        // is the documented "no limit" state for every other field.
        // SAFETY: all-zero is a valid value for this plain-old-data struct.
        let mut info = unsafe { std::mem::zeroed::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() };
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let size = u32::try_from(std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>())
            .map_err(|_| io::Error::from(io::ErrorKind::InvalidInput))?;
        // SAFETY: `info` is a fully initialised struct of exactly `size` bytes and
        // is only read for the duration of the call.
        let ok = unsafe {
            SetInformationJobObject(
                self.0,
                JobObjectExtendedLimitInformation,
                std::ptr::from_ref(&info).cast(),
                size,
            )
        };
        if ok == 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(())
    }

    /// Put `process` (and therefore all of its future children) in this job.
    pub(crate) fn assign(&self, process: HANDLE) -> io::Result<()> {
        if process.is_null() || process == INVALID_HANDLE_VALUE {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "the spawned browser has no process handle to assign",
            ));
        }
        // SAFETY: `process` is the raw handle of the child just spawned and
        // `self.0` is a live job handle; neither is transferred.
        if unsafe { AssignProcessToJobObject(self.0, process) } == 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(())
    }

    /// Terminate every process currently in the job.
    fn terminate(&self) -> io::Result<()> {
        // SAFETY: `self.0` is a live job handle; the exit code is arbitrary.
        if unsafe { TerminateJobObject(self.0, 1) } == 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(())
    }

    /// Live member count as reported by the kernel.
    ///
    /// `None` means the job could not be queried, which is deliberately
    /// distinct from "zero members": a failed read must never be reported as a
    /// clean shutdown.
    fn active_processes(&self) -> Option<u32> {
        // SAFETY: all-zero is a valid value for this plain-old-data struct.
        let mut info = unsafe { std::mem::zeroed::<JOBOBJECT_BASIC_ACCOUNTING_INFORMATION>() };
        let size =
            u32::try_from(std::mem::size_of::<JOBOBJECT_BASIC_ACCOUNTING_INFORMATION>()).ok()?;
        // SAFETY: `info` is valid for writes of `size` bytes for the whole call.
        let ok = unsafe {
            QueryInformationJobObject(
                self.0,
                JobObjectBasicAccountingInformation,
                std::ptr::from_mut(&mut info).cast(),
                size,
                std::ptr::null_mut(),
            )
        };
        (ok != 0).then_some(info.ActiveProcesses)
    }

    /// Pids the kernel reports as members of this job.
    fn member_pids(&self) -> Option<Vec<u32>> {
        // SAFETY: `TH32CS_SNAPPROCESS` asks for the process list only; the
        // process-id argument is ignored for that snapshot kind.
        let snapshot = unsafe { CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0) };
        if snapshot == INVALID_HANDLE_VALUE {
            return None;
        }

        let mut pids = Vec::new();
        let mut entry = PROCESSENTRY32W {
            dwSize: u32::try_from(std::mem::size_of::<PROCESSENTRY32W>()).ok()?,
            ..Default::default()
        };
        // SAFETY: `entry.dwSize` is set as the API requires and `entry` is valid
        // for writes for the duration of each call.
        let mut walking = unsafe { Process32FirstW(snapshot, &mut entry) } != 0;
        while walking {
            if self.contains(entry.th32ProcessID) {
                pids.push(entry.th32ProcessID);
            }
            // SAFETY: identical contract to `Process32FirstW`.
            walking = unsafe { Process32NextW(snapshot, &mut entry) } != 0;
        }
        // SAFETY: `snapshot` came from `CreateToolhelp32Snapshot` and is closed
        // exactly once, here.
        unsafe { CloseHandle(snapshot) };
        Some(pids)
    }

    /// Whether `pid` is a member of this job.
    fn contains(&self, pid: u32) -> bool {
        // SAFETY: the requested access is read-only metadata; a null return is
        // handled without using the handle.
        let process = unsafe { OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid) };
        if process.is_null() {
            return false;
        }
        let mut member: BOOL = 0;
        // SAFETY: both handles are live and `member` is a valid BOOL out-param.
        let ok = unsafe { IsProcessInJob(process, self.0, &mut member) };
        // SAFETY: `process` came from `OpenProcess` and is closed exactly once.
        unsafe { CloseHandle(process) };
        ok != 0 && member != 0
    }
}

impl Drop for JobHandle {
    fn drop(&mut self) {
        // SAFETY: `self.0` is owned solely by this value and closed exactly once.
        // Closing the last handle triggers `KILL_ON_JOB_CLOSE`.
        unsafe { CloseHandle(self.0) };
    }
}

/// Terminate every process in `job`, then prove the job is empty.
///
/// Step for step this mirrors `process_tree::terminate_group`, with the scope
/// switched from a POSIX process group to a job object:
/// 1. `TerminateJobObject`, bounded wait for the kernel to finish the tree kill.
/// 2. `TerminateJobObject` again, bounded wait.
/// 3. Bounded straggler pass that individually terminates every remaining
///    *member* - still job-scoped, so no foreign process can be named here.
///
/// Windows has no `SIGTERM` for another process tree, so the first two steps are
/// both forceful; the grace budgets are time for the kernel to complete the kill
/// rather than an opportunity for Chrome to exit on its own.
///
/// Returns `Err(CdpError::Timeout)` naming the survivors if anything is still a
/// member after all three steps, so callers never report a closed browser that
/// is still running.
pub(crate) async fn terminate_tree(job: &JobHandle, user_data_dir: &Path) -> Result<()> {
    let _ = job.terminate();
    if wait_empty(job, TERM_GRACE).await {
        return Ok(());
    }

    let _ = job.terminate();
    if wait_empty(job, KILL_GRACE).await {
        return Ok(());
    }

    for _ in 0..20 {
        let Some(survivors) = job.member_pids() else {
            break;
        };
        if survivors.is_empty() {
            return Ok(());
        }
        for pid in &survivors {
            terminate_pid(*pid);
        }
        tokio::time::sleep(POLL_INTERVAL).await;
    }

    match job.member_pids() {
        Some(survivors) if survivors.is_empty() => Ok(()),
        Some(survivors) => Err(CdpError::Timeout(format!(
            "browser job survived shutdown; still running with {}: {:?}",
            user_data_dir.display(),
            survivors
        ))),
        None => Err(CdpError::Timeout(format!(
            "could not verify that the browser job is gone: the process table could not be \
             read for {}",
            user_data_dir.display()
        ))),
    }
}

/// Wait until the job reports no live members.
async fn wait_empty(job: &JobHandle, budget: Duration) -> bool {
    let deadline = tokio::time::Instant::now() + budget;
    loop {
        // Accounting is one cheap query; the process-table walk is only paid for
        // once accounting claims the job is empty, to catch a member the
        // accounting structure has not noticed yet.
        if job.active_processes() == Some(0) && matches!(job.member_pids().as_deref(), Some([])) {
            return true;
        }
        if tokio::time::Instant::now() >= deadline {
            return false;
        }
        tokio::time::sleep(POLL_INTERVAL).await;
    }
}

/// Terminate one process by pid.
///
/// Only called for pids the kernel reported as members of this launch's own
/// job. A pid that has already exited makes `OpenProcess` fail, which is the
/// desired no-op.
fn terminate_pid(pid: u32) {
    // SAFETY: the only requested right is `PROCESS_TERMINATE` on a pid already
    // verified to be in this launch's job; a null return is handled without
    // using the handle.
    let process = unsafe { OpenProcess(PROCESS_TERMINATE, 0, pid) };
    if process.is_null() {
        return;
    }
    // SAFETY: `process` is a live handle with `PROCESS_TERMINATE`.
    unsafe { TerminateProcess(process, 1) };
    // SAFETY: `process` came from `OpenProcess` and is closed exactly once.
    unsafe { CloseHandle(process) };
}
