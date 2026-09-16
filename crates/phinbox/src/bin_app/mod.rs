//! `phinbox-app` — macOS .app bundle entry point.
//!
//! Launches the Phinbox daemon with tray icon enabled and opens the
//! inbox in the native SwiftUI helper window. Compiled with `--features tray-native`.
//!
//! On macOS, the tray icon (NSStatusItem) MUST be created on the main
//! thread, and the main thread must run the Cocoa event loop. This binary
//! handles that correctly:
//!
//! 1. Main thread: initialize NSApplication, create tray, run event loop
//! 2. Background thread: start the HTTP daemon (no tray -- the main thread owns it)

mod helper;
mod tray;

use std::path::PathBuf;
use std::sync::{Arc, Condvar, Mutex};

fn main() {
    let inbox_dir: PathBuf = std::env::var("PHINBOX_INBOX_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|_| dirs_bridge().join("Phinbox"));

    let port: u16 = std::env::var("PHINBOX_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(7117);

    let _ = std::fs::create_dir_all(&inbox_dir);

    let notify = phinbox::NotifyChannels {
        imessage_target: std::env::var("PHINBOX_IMESSAGE_TARGET").ok(),
        email_target: std::env::var("PHINBOX_EMAIL_TARGET").ok(),
        webhook_url: std::env::var("PHINBOX_WEBHOOK_URL").ok(),
        native: true,
    };

    // Start daemon on background thread (without tray -- we create it on main)
    let cfg = phinbox::inbox::daemon::DaemonConfig {
        inbox_root: inbox_dir,
        port,
        bind: "127.0.0.1".parse().unwrap(),
        notify,
        enable_tray: false, // we create the tray on the main thread
    };

    // Try to start the daemon. If one is already running on this port,
    // read the lockfile to reuse its port/inbox_root for the tray.
    let (handle, owns_daemon) = match phinbox::inbox::daemon::start_daemon(cfg.clone())
    {
        Ok(h) => (h, true),
        Err(e) => {
            let msg = e.to_string();
            if msg.contains("daemon already running") {
                if let Some(lf) =
                    phinbox::inbox::daemon::lockfile::read_lockfile(&cfg.inbox_root)
                {
                    eprintln!(
                        "phinbox: reusing existing daemon on port {}",
                        lf.port
                    );
                    (
                        phinbox::inbox::daemon::DaemonHandle {
                            port: lf.port,
                            inbox_root: lf.root,
                            bind_addr: lf.bind,
                            lockfile: cfg
                                .inbox_root
                                .join(phinbox::inbox::daemon::lockfile::LOCKFILE_NAME),
                            shutdown: std::sync::Arc::new(
                                std::sync::atomic::AtomicBool::new(false),
                            ),
                        },
                        false,
                    )
                } else {
                    eprintln!("phinbox: daemon running but lockfile unreadable: {e}");
                    std::process::exit(1);
                }
            } else {
                eprintln!("phinbox: failed to start daemon: {e}");
                std::process::exit(1);
            }
        }
    };

    // Open inbox in the native Swift helper window
    helper::launch_inbox_helper(handle.port);

    eprintln!("phinbox: daemon running on http://127.0.0.1:{}", handle.port);

    // On macOS: create tray on main thread and run Cocoa event loop
    #[cfg(target_os = "macos")]
    {
        tray::create_tray_and_run_event_loop(handle, owns_daemon);
    }

    // On other platforms: just block until shutdown
    #[cfg(not(target_os = "macos"))]
    {
        daemon_shutdown_signal();
        let _ = handle.stop();
    }
}

fn dirs_bridge() -> PathBuf {
    std::env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/tmp"))
        .join(".phinbox")
}

pub(crate) fn daemon_shutdown_signal() {
    let state = Arc::new((Mutex::new(false), Condvar::new()));
    let state_for_thread = state.clone();
    std::thread::spawn(move || {
        wait_for_termination();
        let (lock, cv) = &*state_for_thread;
        *lock.lock().unwrap() = true;
        cv.notify_all();
    });
    let (lock, cv) = &*state;
    let mut signaled = lock.lock().unwrap();
    while !*signaled {
        signaled = cv.wait(signaled).unwrap();
    }
}

#[cfg(unix)]
fn wait_for_termination() {
    use std::os::raw::c_int;
    extern "C" {
        fn signal(sig: c_int, handler: extern "C" fn(c_int)) -> extern "C" fn(c_int);
    }
    extern "C" fn handler(_sig: c_int) {
        std::process::exit(0);
    }
    unsafe {
        signal(2, handler); // SIGINT
        signal(15, handler); // SIGTERM
        signal(1, handler); // SIGHUP
    }
    loop {
        std::thread::park();
    }
}
