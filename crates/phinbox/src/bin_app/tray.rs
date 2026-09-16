//! Tray event dispatch and inbox-helper activation.

/// Dispatch tray events by activating the native inbox-helper window
/// instead of opening a browser. Runs on a background thread.
pub(crate) fn tray_event_dispatch(
    tray: &dyn phinbox::Tray,
    shutdown: &std::sync::atomic::AtomicBool,
    port: u16,
) {
    use std::sync::atomic::Ordering;
    use std::thread;
    use std::time::Duration;

    while !shutdown.load(Ordering::SeqCst) {
        let Some(event) = tray.try_recv() else {
            thread::sleep(Duration::from_millis(100));
            continue;
        };
        match event {
            phinbox::tray::TrayEvent::Click | phinbox::tray::TrayEvent::DoubleClick => {
                activate_inbox_helper(port);
            }
            phinbox::tray::TrayEvent::MenuItem { id } => {
                use phinbox::tray::MenuAction;
                let action = match id.as_str() {
                    x if x == MenuAction::OpenInbox.id() => Some(MenuAction::OpenInbox),
                    x if x == MenuAction::OpenLatest.id() => Some(MenuAction::OpenLatest),
                    x if x == MenuAction::ToggleQuiet.id() => Some(MenuAction::ToggleQuiet),
                    x if x == MenuAction::Quit.id() => Some(MenuAction::Quit),
                    _ => None,
                };
                if let Some(a) = action {
                    match a {
                        MenuAction::OpenInbox => {
                            activate_inbox_helper(port);
                        }
                        MenuAction::OpenLatest => {
                            activate_inbox_helper(port);
                        }
                        MenuAction::ToggleQuiet => {
                            let _ = tray.set_tooltip("phinbox inbox (quiet)");
                        }
                        MenuAction::Quit => {
                            tracing::info!("quit requested from tray");
                            shutdown.store(true, Ordering::SeqCst);
                            break;
                        }
                    }
                }
            }
        }
    }
}

/// Bring the inbox-helper window to the foreground on macOS.
/// Sends SIGUSR1 to the inbox-helper process, which activates its window.
fn activate_inbox_helper(port: u16) {
    use std::process::Command;

    // Find the inbox-helper PID and send SIGUSR1 (signal 30 on macOS)
    if let Ok(output) = Command::new("pgrep").arg("inbox-helper").output() {
        if let Some(pid_str) = String::from_utf8_lossy(&output.stdout).lines().next() {
            if !pid_str.trim().is_empty() {
                let _ = Command::new("kill")
                    .args(["-USR1", pid_str.trim()])
                    .output();
                return;
            }
        }
    }

    // Fallback: launch inbox-helper if not running
    let exe = std::env::current_exe().ok();
    let exe_dir = exe.as_ref().and_then(|p| p.parent());
    if let Some(dir) = exe_dir {
        let helper = dir.join("../Resources/inbox-helper");
        if helper.exists() {
            let url = format!("http://127.0.0.1:{}/inbox/", port);
            let _ = Command::new(helper).arg(&url).spawn();
            return;
        }
        let helper_flat = dir.join("inbox-helper");
        if helper_flat.exists() {
            let url = format!("http://127.0.0.1:{}/inbox/", port);
            let _ = Command::new(helper_flat).arg(&url).spawn();
            return;
        }
    }

    // Last resort: open in browser
    let url = format!("http://127.0.0.1:{}/inbox/", port);
    let _ = Command::new("open").arg(&url).spawn();
}

#[cfg(target_os = "macos")]
pub(crate) fn create_tray_and_run_event_loop(
    handle: phinbox::inbox::daemon::DaemonHandle,
    owns_daemon: bool,
) {
    use objc2_app_kit::{NSApplication, NSApplicationActivationPolicy};
    use objc2_foundation::{NSTimer, MainThreadMarker};
    use objc2::rc::Retained;
    use std::sync::Arc;

    let mtm = match MainThreadMarker::new() {
        Some(m) => m,
        None => {
            eprintln!("phinbox: not on main thread, cannot create tray");
            super::daemon_shutdown_signal();
            if owns_daemon { let _ = handle.stop(); }
            return;
        }
    };

    // Initialize NSApplication (required for tray icon event loop)
    let app = NSApplication::sharedApplication(mtm);
    app.setActivationPolicy(NSApplicationActivationPolicy::Accessory);

    // Create tray on main thread (has MainThreadMarker)
    let tray_url = format!("http://127.0.0.1:{}", handle.port);
    let tray_cfg = phinbox::TrayConfig::new(tray_url, &handle.inbox_root);
    let tray = match phinbox::build_tray(tray_cfg) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("phinbox: tray creation failed: {e}");
            super::daemon_shutdown_signal();
            if owns_daemon { let _ = handle.stop(); }
            return;
        }
    };
    eprintln!("phinbox: tray icon created (backend: {})", tray.backend_name());

    // Schedule an NSTimer on the main RunLoop to pump tray events.
    unsafe {
        let mut block = block2::StackBlock::new(|_timer: std::ptr::NonNull<NSTimer>| {
            phinbox::tray::poll_tray();
        });
        let _timer: Retained<NSTimer> = NSTimer::scheduledTimerWithTimeInterval_repeats_block(
            0.1, true, &mut block,
        );
    }

    // Dispatch tray events on a background thread.
    let shutdown = Arc::new(std::sync::atomic::AtomicBool::new(false));
    {
        let tray_ref = tray.clone();
        let shutdown_ref = shutdown.clone();
        let port = handle.port;
        std::thread::Builder::new()
            .name("phinbox-tray-events".into())
            .spawn(move || {
                tray_event_dispatch(tray_ref.as_ref(), &shutdown_ref, port);
            })
            .ok();
    }

    // Run Cocoa event loop on main thread (blocks until app terminates)
    app.run();

    // Cleanup
    shutdown.store(true, std::sync::atomic::Ordering::SeqCst);
    let _ = tray.shutdown();
    if owns_daemon {
        let _ = handle.stop();
    }
}
