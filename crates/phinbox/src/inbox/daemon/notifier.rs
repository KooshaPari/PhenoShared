//! Notifier poller and tray event pump for the inbox daemon.
//!
//! The notifier loop scans the inbox directory for new pending requests
//! and surfaces them via the configured notification channels (tray,
//! iMessage, email, webhook). The tray event pump dispatches menu
//! actions from the OS tray icon.

use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, Instant};

use crate::inbox::notify::{NotifyChannels, surface_all};
use crate::inbox::{mark_expired_in_place, list_pending, RequestState};
use crate::tray::{MenuAction, Tray, TrayEvent};
use tracing::{debug, info, warn};

/// How often the daemon scans the inbox dir for new entries.
const POLL_INTERVAL: Duration = Duration::from_millis(500);

/// Run the notifier loop: poll the inbox directory and surface new
/// requests via the configured notification channels.
pub(crate) fn run_notifier_loop(
    inbox_root: &Path,
    cfg: NotifyChannels,
    shutdown: &Arc<AtomicBool>,
    tray: Option<Arc<dyn Tray>>,
) {
    let mut seen: std::collections::HashSet<String> = std::collections::HashSet::new();
    let deadline = Instant::now() + Duration::from_secs(60 * 60 * 24); // safety net
    while !shutdown.load(Ordering::SeqCst) && Instant::now() < deadline {
        match list_pending(inbox_root) {
            Ok(requests) => {
                let pending_count = requests
                    .iter()
                    .filter(|r| matches!(r.state, RequestState::Pending))
                    .count();
                // Keep the tray badge in sync with the pending count.
                if let Some(t) = &tray {
                    let badge: String = if pending_count == 0 {
                        String::new()
                    } else if pending_count >= 10 {
                        "9+".to_string()
                    } else {
                        pending_count.to_string()
                    };
                    let _ = t.set_badge(&badge);
                }
                for req in requests {
                    if seen.contains(&req.request_id) {
                        continue;
                    }
                    seen.insert(req.request_id.clone());
                    if matches!(req.state, RequestState::Pending) {
                        info!(request_id = %req.request_id, "surfacing new request");
                        let attempts = surface_all(&req, &cfg);
                        for a in attempts {
                            debug!(
                                request_id = %req.request_id,
                                kind = ?a.kind,
                                ok = a.ok,
                                detail = %a.detail,
                                "notification attempt"
                            );
                        }
                    }
                }
            }
            Err(e) => warn!(error = %e, "inbox scan failed"),
        }
        // Reap expired requests every minute-ish (cheap, no separate timer).
        // Expired requests are marked in-place within inbox/ so the inbox UI
        // can still render them (greyed-out / expired badge). They are NOT
        // moved to answered/ — that only happens when the user explicitly
        // answers or cancels.
        if let Ok(reqs) = list_pending(inbox_root) {
            for mut req in reqs {
                if req.is_expired_now() && !req.is_terminal() {
                    req.state = RequestState::Expired;
                    if let Err(e) = mark_expired_in_place(inbox_root, &req) {
                        warn!(error = %e, request_id = %req.request_id, "failed to expire");
                    }
                }
            }
        }
        thread::sleep(POLL_INTERVAL);
    }
}

/// Long-running loop that dispatches menu events from the tray icon.
/// Runs on its own thread; exits when `shutdown` flips or the OS tray
/// thread terminates.
pub fn run_tray_loop(
    tray: &dyn Tray,
    shutdown: &Arc<AtomicBool>,
    fallback_url: &str,
) {
    while !shutdown.load(Ordering::SeqCst) {
        let Some(event) = tray.try_recv() else {
            thread::sleep(Duration::from_millis(100));
            continue;
        };
        match event {
            TrayEvent::Click | TrayEvent::DoubleClick => {
                let url = tray_click_url(tray, fallback_url);
                let _ = open_in_default_browser(&url);
            }
            TrayEvent::MenuItem { id } => {
                let action = match id.as_str() {
                    x if x == MenuAction::OpenInbox.id() => Some(MenuAction::OpenInbox),
                    x if x == MenuAction::OpenLatest.id() => Some(MenuAction::OpenLatest),
                    x if x == MenuAction::ToggleQuiet.id() => Some(MenuAction::ToggleQuiet),
                    x if x == MenuAction::Quit.id() => Some(MenuAction::Quit),
                    _ => None,
                };
                if let Some(a) = action {
                    let base = tray_click_url(tray, fallback_url);
                    match a {
                        MenuAction::OpenInbox => {
                            let _ = open_in_default_browser(&base);
                        }
                        MenuAction::OpenLatest => {
                            let url = format!("{base}/inbox/latest");
                            let _ = open_in_default_browser(&url);
                        }
                        MenuAction::ToggleQuiet => {
                            let _ = tray.set_tooltip("phinbox inbox (quiet)");
                        }
                        MenuAction::Quit => {
                            info!("quit requested from tray");
                            shutdown.store(true, Ordering::SeqCst);
                            break;
                        }
                    }
                }
            }
        }
    }
}

/// Extract the tray's bound URL (from its config) — used as the
/// click-to-open target. Falls back to the daemon's actual bind
/// URL if the tray doesn't expose one (legacy `NoopTray` configs).
fn tray_click_url(tray: &dyn Tray, fallback: &str) -> String {
    tray.inbox_url().map_or_else(|| fallback.trim_end_matches('/').to_string(), |u| u.trim_end_matches('/').to_string())
}

/// Open `url` in the user's default browser. Best-effort; failures
/// only log at debug level — the tray click UX degrades gracefully to
/// "nothing visible happened" if there's no browser.
pub(crate) fn open_in_default_browser(url: &str) -> std::io::Result<()> {
    use std::process::Command;
    #[cfg(target_os = "macos")]
    {
        Command::new("open").arg(url).spawn().map(|_| ())
    }
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", url])
            .spawn()
            .map(|_| ())
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open").arg(url).spawn().map(|_| ())
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
    {
        let _ = url;
        Ok(())
    }
}
