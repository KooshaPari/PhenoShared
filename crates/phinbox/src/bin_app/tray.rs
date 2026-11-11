//! Tray event dispatch and inbox-helper activation.

/// Dispatch tray events by activating the native inbox-helper window
/// instead of opening a browser. Runs on a background thread.
pub(crate) fn tray_event_dispatch(
    tray: &dyn phinbox::Tray,
    shutdown: &std::sync::atomic::AtomicBool,
    port: u16,
    root: &std::path::Path,
) {
    use std::{sync::atomic::Ordering, thread, time::Duration};

    while !shutdown.load(Ordering::SeqCst) {
        let Some(event) = tray.try_recv() else {
            thread::sleep(Duration::from_millis(100));
            continue;
        };
        match event {
            phinbox::tray::TrayEvent::Click | phinbox::tray::TrayEvent::DoubleClick => {
                super::helper::activate(port, root);
            },
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
                            super::helper::activate(port, root);
                        },
                        MenuAction::OpenLatest => {
                            super::helper::activate(port, root);
                        },
                        MenuAction::ToggleQuiet => {
                            let _ = tray.set_tooltip("phinbox inbox (quiet)");
                        },
                        MenuAction::Quit => {
                            tracing::info!("quit requested from tray");
                            shutdown.store(true, Ordering::SeqCst);
                            break;
                        },
                    }
                }
            },
        }
    }
}

#[cfg(target_os = "macos")]
pub(crate) fn create_tray_and_run_event_loop(
    handle: phinbox::inbox::daemon::DaemonHandle,
    owns_daemon: bool,
) {
    use std::sync::Arc;

    use objc2::rc::Retained;
    use objc2_app_kit::{NSApplication, NSApplicationActivationPolicy};
    use objc2_foundation::{MainThreadMarker, NSTimer};

    let mtm = match MainThreadMarker::new() {
        Some(m) => m,
        None => {
            eprintln!("phinbox: not on main thread, cannot create tray");
            super::daemon_shutdown_signal();
            if owns_daemon {
                let _ = handle.stop();
            }
            return;
        },
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
            if owns_daemon {
                let _ = handle.stop();
            }
            return;
        },
    };
    eprintln!(
        "phinbox: tray icon created (backend: {})",
        tray.backend_name()
    );

    let shutdown = Arc::new(std::sync::atomic::AtomicBool::new(false));
    // Schedule an NSTimer on the main RunLoop to pump tray events.
    // SAFETY ESCAPE HATCH: `StackBlock` + the objc2 NSTimer entry point are
    // FFI by construction, and a repeating timer must run on the main thread's
    // RunLoop — which is exactly where this is called from. The crate sets
    // `unsafe_code = "deny"`, so this is the same documented hatch used in
    // `cli/open.rs`.
    #[allow(unsafe_code)]
    unsafe {
        let timer_stop = Arc::clone(&shutdown);
        let timer_app = app.clone();
        let timer_tray = tray.clone();
        let timer_root = handle.inbox_root.clone();
        let mut block = block2::StackBlock::new(move |_timer: std::ptr::NonNull<NSTimer>| {
            phinbox::tray::poll_tray();
            let count = phinbox::inbox::list_pending(&timer_root)
                .unwrap_or_default()
                .iter()
                .filter(|r| !r.is_terminal() && !r.is_expired_now())
                .count();
            let _ = timer_tray.set_badge(&if count == 0 {
                String::new()
            } else {
                count.to_string()
            });
            if timer_stop.load(std::sync::atomic::Ordering::SeqCst) {
                timer_app.stop(None);
            }
        });
        let _timer: Retained<NSTimer> =
            NSTimer::scheduledTimerWithTimeInterval_repeats_block(0.5, true, &mut block);
    }

    // Dispatch tray events on a background thread.
    {
        let tray_ref = tray.clone();
        let shutdown_ref = shutdown.clone();
        let port = handle.port;
        let root = handle.inbox_root.clone();
        std::thread::Builder::new()
            .name("phinbox-tray-events".into())
            .spawn(move || {
                tray_event_dispatch(tray_ref.as_ref(), &shutdown_ref, port, &root);
            })
            .ok();
    }

    // Run Cocoa event loop on main thread (blocks until app terminates)
    app.run();

    // Cleanup
    super::helper::stop();
    shutdown.store(true, std::sync::atomic::Ordering::SeqCst);
    let _ = tray.shutdown();
    if owns_daemon {
        let _ = handle.stop();
    }
}
