//! SIGHUP-based reload fallback.
//!
//! For environments without filesystem notifications (some sandboxes, CI
//! runners), this module provides a manual nudge: call `reload()` on any
//! `Reloadable<T>` by sending a SIGHUP signal to the process. The handler
//! is registered once at startup and delegates to a user-provided reload
//! closure.

use std::sync::atomic::{AtomicBool, Ordering};

static HUP_RECEIVED: AtomicBool = AtomicBool::new(false);

/// Register a SIGHUP handler that sets a flag.
///
/// Call [`poll_reload()`] periodically (e.g., from a tokio interval task)
/// to check whether a SIGHUP was received and trigger the reload.
pub fn register_hup_handler() {
    // SAFETY: signal handlers are global; this is safe as long as only
    // one handler is registered. We only register once.
    unsafe {
        libc_signal_hup();
    }
}

#[cfg(unix)]
unsafe fn libc_signal_hup() {
    unsafe extern "C" fn handler(_sig: libc::c_int) {
        HUP_RECEIVED.store(true, Ordering::SeqCst);
    }
    libc::signal(libc::SIGHUP, handler as *const () as libc::sighandler_t);
}

/// Check whether a SIGHUP was received since the last call to this function.
///
/// Returns `true` exactly once per SIGHUP signal (atomic exchange).
pub fn poll_reload() -> bool {
    HUP_RECEIVED.swap(false, Ordering::SeqCst)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sighup_poll_once_per_signal() {
        assert!(!poll_reload(), "no signal yet");
        HUP_RECEIVED.store(true, Ordering::SeqCst);
        assert!(poll_reload(), "signal detected");
        assert!(!poll_reload(), "consumed — second poll returns false");
    }
}
