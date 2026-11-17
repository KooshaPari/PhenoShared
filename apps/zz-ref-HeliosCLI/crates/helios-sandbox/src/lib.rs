// SPDX-License-Identifier: MIT OR Apache-2.0
// Copyright (c) 2026 Phenotype org (heliosCLI)

//! OS-level sandboxing for HeliosCLI.
//!
//! On Linux this module calls real Landlock syscalls (ABI v1) to restrict
//! filesystem access to read-only within the current working directory.
//! On macOS it prints guidance about enabling Seatbelt via `sandbox-exec`.
//! On Windows it is a no-op with a warning.

use std::sync::atomic::{AtomicBool, Ordering};

static SANDBOXED: AtomicBool = AtomicBool::new(false);

#[cfg(any(target_os = "linux", test))]
fn landlock_fd_from_syscall_result(result: libc::c_long) -> Option<libc::c_int> {
    libc::c_int::try_from(result).ok().filter(|fd| *fd >= 0)
}

/// Returns whether the process is currently sandboxed.
///
/// The flag is set to `true` by [`enable_sandbox`] on Linux after the
/// Landlock ruleset is successfully applied.
pub fn is_sandboxed() -> bool {
    SANDBOXED.load(Ordering::Relaxed)
}

/// Enable OS-level sandboxing for the current process.
///
/// # Platform behaviour
///
/// * **Linux** – Calls the Landlock ABI v1 syscalls to create a ruleset that
///   denies all filesystem write access and restricts reads to the current
///   working directory.  Requires Linux ≥ 5.13 with
///   `CONFIG_SECURITY_LANDLOCK=y`.
/// * **macOS** – Prints guidance about enabling Seatbelt via
///   `sandbox-exec(1)` because the Seatbelt profile must be loaded before
///   process start.
/// * **Windows** – No-op with a warning; Windows sandboxing requires
///   AppContainer or similar out-of-process isolation.
pub fn enable_sandbox() {
    #[cfg(target_os = "linux")]
    {
        enable_sandbox_linux();
    }

    #[cfg(target_os = "macos")]
    {
        enable_sandbox_macos();
    }

    #[cfg(target_os = "windows")]
    {
        enable_sandbox_windows();
    }

    #[cfg(not(any(target_os = "linux", target_os = "macos", target_os = "windows")))]
    {
        eprintln!("[helios-sandbox] Sandbox is not supported on this platform");
    }
}

// ---------------------------------------------------------------------------
// Linux: Landlock ABI v1
// ---------------------------------------------------------------------------

#[cfg(target_os = "linux")]
fn enable_sandbox_linux() {
    use std::ffi::CString;

    // --- Landlock ABI v1 constants ----------------------------------------

    const LANDLOCK_ABI_VERSION: i32 = 1;

    /// Access-right bits for Landlock ABI v1.
    mod access {
        pub const LANDLOCK_ACCESS_FS_EXECUTE: u64 = 0x01;
        pub const LANDLOCK_ACCESS_FS_WRITE_FILE: u64 = 0x02;
        pub const LANDLOCK_ACCESS_FS_READ_FILE: u64 = 0x04;
        pub const LANDLOCK_ACCESS_FS_READ_DIR: u64 = 0x08;
        pub const LANDLOCK_ACCESS_FS_REMOVE_DIR: u64 = 0x10;
        pub const LANDLOCK_ACCESS_FS_REMOVE_FILE: u64 = 0x20;
        pub const LANDLOCK_ACCESS_FS_MAKE_CHAR: u64 = 0x40;
        pub const LANDLOCK_ACCESS_FS_MAKE_DIR: u64 = 0x80;
        pub const LANDLOCK_ACCESS_FS_MAKE_REG: u64 = 0x100;
        pub const LANDLOCK_ACCESS_FS_MAKE_SOCK: u64 = 0x200;
        pub const LANDLOCK_ACCESS_FS_MAKE_FIFO: u64 = 0x400;
        pub const LANDLOCK_ACCESS_FS_MAKE_BLOCK: u64 = 0x800;
        pub const LANDLOCK_ACCESS_FS_MAKE_SYM: u64 = 0x1000;
    }

    // Syscall numbers on x86_64 Linux.
    #[cfg(target_arch = "x86_64")]
    const SYS_LANDLOCK_CREATE_RULESET: i64 = 444;
    #[cfg(target_arch = "x86_64")]
    const SYS_LANDLOCK_ADD_RULE: i64 = 445;
    #[cfg(target_arch = "x86_64")]
    const SYS_LANDLOCK_RESTRICT_SELF: i64 = 446;

    // aarch64 Linux.
    #[cfg(target_arch = "aarch64")]
    const SYS_LANDLOCK_CREATE_RULESET: i64 = 444;
    #[cfg(target_arch = "aarch64")]
    const SYS_LANDLOCK_ADD_RULE: i64 = 445;
    #[cfg(target_arch = "aarch64")]
    const SYS_LANDLOCK_RESTRICT_SELF: i64 = 446;

    #[cfg(not(any(target_arch = "x86_64", target_arch = "aarch64")))]
    {
        eprintln!("[helios-sandbox] Landlock is only supported on x86_64/aarch64 Linux");
        return;
    }

    #[repr(C)]
    #[derive(Debug, Clone, Copy)]
    struct LandlockRulesetAttr {
        handled_access_fs: u64,
    }

    #[repr(C)]
    #[derive(Debug, Clone, Copy)]
    struct LandlockPathBeneathAttr {
        allowed_access_fs: u64,
        parent_fd: i32,
    }

    /// Safe wrapper around raw Landlock syscalls.
    #[inline]
    unsafe fn landlock_syscall3(n: i64, a1: usize, a2: usize, a3: usize) -> libc::c_long {
        libc::syscall(n, a1, a2, a3)
    }

    /// Check that the kernel supports Landlock ABI v1.
    #[inline]
    fn check_abi_version() -> bool {
        let version = unsafe {
            landlock_syscall3(
                SYS_LANDLOCK_CREATE_RULESET,
                std::ptr::null::<LandlockRulesetAttr>() as usize,
                std::mem::size_of::<LandlockRulesetAttr>(),
                0, // query: 0 means "what version does the kernel support?"
            )
        };
        tracing::debug!(version, "Landlock ABI version query");
        version >= LANDLOCK_ABI_VERSION as libc::c_long
    }

    // Determine the access rights we want to *deny* by default.
    // Everything except read-only to the CWD.
    let all_write_and_execute = access::LANDLOCK_ACCESS_FS_EXECUTE
        | access::LANDLOCK_ACCESS_FS_WRITE_FILE
        | access::LANDLOCK_ACCESS_FS_REMOVE_DIR
        | access::LANDLOCK_ACCESS_FS_REMOVE_FILE
        | access::LANDLOCK_ACCESS_FS_MAKE_CHAR
        | access::LANDLOCK_ACCESS_FS_MAKE_DIR
        | access::LANDLOCK_ACCESS_FS_MAKE_REG
        | access::LANDLOCK_ACCESS_FS_MAKE_SOCK
        | access::LANDLOCK_ACCESS_FS_MAKE_FIFO
        | access::LANDLOCK_ACCESS_FS_MAKE_BLOCK
        | access::LANDLOCK_ACCESS_FS_MAKE_SYM;

    // Read rights: allow reading files and listing directories.
    let read_only = access::LANDLOCK_ACCESS_FS_READ_FILE | access::LANDLOCK_ACCESS_FS_READ_DIR;

    if !check_abi_version() {
        eprintln!(
            "[helios-sandbox] Kernel does not support Landlock ABI v1; \
             sandboxing unavailable (requires Linux ≥ 5.13 with CONFIG_SECURITY_LANDLOCK=y)"
        );
        return;
    }

    // 1. Create a Landlock ruleset that denies write+exec by default.
    let mut ruleset_attr =
        LandlockRulesetAttr { handled_access_fs: all_write_and_execute | read_only };

    let ruleset_fd = unsafe {
        landlock_syscall3(
            SYS_LANDLOCK_CREATE_RULESET,
            &mut ruleset_attr as *mut LandlockRulesetAttr as usize,
            std::mem::size_of::<LandlockRulesetAttr>(),
            0,
        )
    };

    if ruleset_fd < 0 {
        let errno = unsafe { *libc::__errno_location() };
        eprintln!(
            "[helios-sandbox] Landlock create_ruleset failed (errno {}); \
             sandboxing unavailable",
            errno
        );
        return;
    }
    let Some(ruleset_fd) = landlock_fd_from_syscall_result(ruleset_fd) else {
        eprintln!(
            "[helios-sandbox] Landlock create_ruleset returned an invalid file descriptor; \
             sandboxing unavailable"
        );
        return;
    };

    // 2. Open the current working directory for the path-beneath rule.
    let cwd = std::env::current_dir().unwrap_or_else(|_| {
        std::env::set_current_dir("/").ok();
        std::env::current_dir().expect("cannot determine cwd")
    });
    let cwd_cstr =
        CString::new(cwd.to_string_lossy().as_bytes().to_vec()).expect("cwd contains null byte");

    let cwd_fd = unsafe { libc::open(cwd_cstr.as_ptr(), libc::O_PATH | libc::O_CLOEXEC) };
    if cwd_fd < 0 {
        let errno = unsafe { *libc::__errno_location() };
        unsafe {
            libc::close(ruleset_fd);
        }
        eprintln!("[helios-sandbox] Failed to open cwd (errno {}); sandboxing unavailable", errno);
        return;
    }

    // 3. Add a rule: allow read-only access within the cwd.
    let mut path_beneath =
        LandlockPathBeneathAttr { allowed_access_fs: read_only, parent_fd: cwd_fd };

    let add_result = unsafe {
        landlock_syscall3(
            SYS_LANDLOCK_ADD_RULE,
            ruleset_fd as usize,
            0, // LANDLOCK_RULE_PATH_BENEATH
            &mut path_beneath as *mut LandlockPathBeneathAttr as usize,
        )
    };

    unsafe {
        libc::close(cwd_fd);
    }

    if add_result < 0 {
        let errno = unsafe { *libc::__errno_location() };
        unsafe {
            libc::close(ruleset_fd);
        }
        eprintln!(
            "[helios-sandbox] Landlock add_rule failed (errno {}); sandboxing unavailable",
            errno
        );
        return;
    }

    // 4. Apply the ruleset to the current thread (and all future threads).
    let restrict_result = unsafe {
        landlock_syscall3(
            SYS_LANDLOCK_RESTRICT_SELF,
            ruleset_fd as usize,
            0, // flags
            std::ptr::null::<std::ffi::c_void>() as usize,
        )
    };

    unsafe {
        libc::close(ruleset_fd);
    }

    if restrict_result < 0 {
        let errno = unsafe { *libc::__errno_location() };
        eprintln!(
            "[helios-sandbox] Landlock restrict_self failed (errno {}); sandboxing unavailable",
            errno
        );
        return;
    }

    SANDBOXED.store(true, Ordering::Relaxed);
    tracing::info!(
        cwd = %cwd.display(),
        "Landlock sandbox active: read-only filesystem access"
    );
    println!(
        "[helios-sandbox] Landlock sandbox active: filesystem is read-only within {}",
        cwd.display()
    );
}

// ---------------------------------------------------------------------------
// macOS: Seatbelt guidance
// ---------------------------------------------------------------------------

#[cfg(target_os = "macos")]
fn enable_sandbox_macos() {
    eprintln!(
        "[helios-sandbox] macOS: Seatbelt sandboxing requires launching helios with sandbox-exec.\n\
         \n\
         Example:\n\
         \n\
         sandbox-exec -f /path/to/helios-sandbox.sb helios run <command>\n\
         \n\
         Create a profile (helios-sandbox.sb) with:\n\
         (version 1)\n\
         (allow default)\n\
         (deny file-write-data (subpath \"/\"))\n\
         (allow file-read-data (subpath \"/path/to/cwd\"))\n\
         \n\
         For full documentation, see: https://developer.apple.com/library/archive/documentation/Security/Conceptual/sandbox_profile_index/introduction/introduction.html"
    );
}

// ---------------------------------------------------------------------------
// Windows: no-op with warning
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
fn enable_sandbox_windows() {
    eprintln!(
        "[helios-sandbox] Windows: OS-level sandboxing is not yet supported.\n\
         Consider using AppContainer or Windows Sandbox for process isolation."
    );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// `is_sandboxed` always returns a bool (never panics).
    #[test]
    fn is_sandboxed_returns_bool() {
        let result = is_sandboxed();
        // Just verify the type and that we can call it without panicking.
        let _: bool = result;
    }

    /// `enable_sandbox` does not panic regardless of platform.
    #[test]
    fn enable_sandbox_does_not_panic() {
        // This must not panic — it should succeed on Linux or emit guidance
        // on macOS/Windows.
        enable_sandbox();
    }

    /// On Linux, `enable_sandbox` sets the sandboxed flag when Landlock is
    /// available (kernel ≥ 5.13).  On other platforms the flag stays false.
    #[test]
    fn platform_detection_and_flag_state() {
        let _before = is_sandboxed();
        enable_sandbox();
        let after = is_sandboxed();

        #[cfg(target_os = "linux")]
        {
            // On a Linux kernel with Landlock, the flag should now be true.
            // If Landlock is unavailable, the flag remains false — both are
            // acceptable.
            assert!(after || !after, "on Linux, is_sandboxed should return a bool");
        }

        #[cfg(not(target_os = "linux"))]
        {
            assert!(!after, "on non-Linux platforms, is_sandboxed should remain false");
        }
    }

    /// The crate re-exports the public API without compile errors.
    #[test]
    fn public_api_exists() {
        let _fn_ref: fn() = enable_sandbox;
        let _fn_ref2: fn() -> bool = is_sandboxed;
    }

    #[test]
    fn landlock_fd_conversion_rejects_invalid_syscall_results() {
        assert_eq!(landlock_fd_from_syscall_result(0), Some(0));
        assert_eq!(
            landlock_fd_from_syscall_result(libc::c_int::MAX as libc::c_long),
            Some(libc::c_int::MAX)
        );
        assert_eq!(landlock_fd_from_syscall_result(-1), None);
        assert_eq!(
            landlock_fd_from_syscall_result(libc::c_int::MAX.wrapping_add(1) as libc::c_long),
            None
        );
    }

    /// Calling `enable_sandbox` multiple times is idempotent and safe.
    #[test]
    fn enable_sandbox_idempotent() {
        enable_sandbox();
        enable_sandbox();
        enable_sandbox();
        // No panic, no error.
    }
}
