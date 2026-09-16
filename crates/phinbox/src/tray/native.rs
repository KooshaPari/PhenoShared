//! Real OS tray backend — compiled only with `--features tray-native`.
//!
//! Uses `tray-icon` crate (NSStatusItem on macOS, Shell_NotifyIcon on Windows,
//! libappindicator on Linux). On macOS the `TrayIcon` is created and polled on
//! the **main thread** because:
//!
//! 1. `TrayIcon` is `!Send` (Objective-C refs are single-threaded under ARC).
//! 2. NSStatusItem click/menu events only dispatch on the main NSRunLoop.
//!
//! Cross-thread commands (badge, tooltip) arrive via a channel. The main-thread
//! function [`poll_tray`] drains them and applies them to the `TrayIcon`.

use super::{MenuAction, TrayConfig, TrayError, TrayEvent, Tray, TrayResult};
use std::sync::mpsc::{channel, Sender, Receiver};
use tray_icon::{
    menu::{Menu, MenuEvent, MenuItem, PredefinedMenuItem},
    Icon, TrayIconBuilder,
};

// ── Commands from daemon threads to main-thread event pump ───────────────

enum TrayCmd {
    SetBadge { text: String },
    SetTooltip { text: String },
    Shutdown,
}

// ── Static storage (single-instance desktop app) ────────────────────────
//
// SAFETY: All access happens from the macOS main thread.  `poll_tray()` is
// called exclusively from an NSTimer scheduled on the main RunLoop.

static mut TRAY_ICON: Option<tray_icon::TrayIcon> = None;
static mut CMD_RX: Option<Receiver<TrayCmd>> = None;
static mut EV_TX: Option<Sender<TrayEvent>> = None;

/// Create the native tray icon on the calling thread (must be the main thread).
///
/// Returns the `Tray` trait object for sending commands cross-thread and
/// receiving events.
pub fn create_native_tray(cfg: TrayConfig) -> TrayResult<Arc<dyn Tray>> {
    let icon = make_placeholder_icon()?;

    let menu = Menu::new();
    menu.append(&MenuItem::with_id(
        MenuAction::OpenInbox.id(),
        MenuAction::OpenInbox.label(),
        true,
        None,
    ))
    .map_err(map_err)?;
    menu.append(&MenuItem::with_id(
        MenuAction::OpenLatest.id(),
        MenuAction::OpenLatest.label(),
        true,
        None,
    ))
    .map_err(map_err)?;
    menu.append(&MenuItem::with_id(
        MenuAction::ToggleQuiet.id(),
        MenuAction::ToggleQuiet.label(),
        true,
        None,
    ))
    .map_err(map_err)?;
    menu.append(&PredefinedMenuItem::separator()).map_err(map_err)?;
    menu.append(&MenuItem::with_id(
        MenuAction::Quit.id(),
        MenuAction::Quit.label(),
        true,
        None,
    ))
    .map_err(map_err)?;

    let mut builder = TrayIconBuilder::new()
        .with_tooltip(&cfg.tooltip)
        .with_icon(icon)
        .with_menu(Box::new(menu));
    if !cfg.initial_badge.is_empty() {
        builder = builder.with_title(&cfg.initial_badge);
    }
    let tray_icon = builder
        .build()
        .map_err(|e| TrayError::NotAvailable(e.to_string()))?;

    let (cmd_tx, cmd_rx) = channel::<TrayCmd>();
    let (ev_tx, ev_rx) = channel::<TrayEvent>();

    // Store in statics for the main-thread pump.
    // SAFETY: single-instance app, all access from main thread.
    unsafe {
        TRAY_ICON = Some(tray_icon);
        CMD_RX = Some(cmd_rx);
        EV_TX = Some(ev_tx);
    }

    Ok(Arc::new(StaticTray { cmd_tx, ev_rx: std::sync::Mutex::new(ev_rx), cfg }))
}

/// Drain pending commands and forward tray events.
/// Call this from an NSTimer on the main thread (e.g. every 100ms).
pub fn poll_tray() {
    // SAFETY: called only from main thread after `create_native_tray`.
    let (cmd_rx, ev_tx) = unsafe {
        match (&CMD_RX, &EV_TX) {
            (Some(rx), Some(tx)) => (rx, tx),
            _ => return, // tray not initialized
        }
    };

    // Drain commands → apply to TrayIcon.
    loop {
        match cmd_rx.try_recv() {
            Ok(TrayCmd::SetBadge { text }) => {
                unsafe {
                    if let Some(ref tray) = TRAY_ICON {
                        let _ = tray.set_title(Some(text.clone()));
                        let tip = format!("phinbox inbox · {} pending", text);
                        let _ = tray.set_tooltip(Some(tip));
                    }
                }
            }
            Ok(TrayCmd::SetTooltip { text }) => {
                unsafe {
                    if let Some(ref tray) = TRAY_ICON {
                        let _ = tray.set_tooltip(Some(text));
                    }
                }
            }
            Ok(TrayCmd::Shutdown) => {
                unsafe { TRAY_ICON = None; }
                return;
            }
            Err(std::sync::mpsc::TryRecvError::Empty) => break,
            Err(std::sync::mpsc::TryRecvError::Disconnected) => break,
        }
    }

    // Forward tray-icon click events.
    if let Ok(ev) = tray_icon::TrayIconEvent::receiver().try_recv() {
        let mapped = match ev {
            tray_icon::TrayIconEvent::Click { .. } => Some(TrayEvent::Click),
            tray_icon::TrayIconEvent::DoubleClick { .. } => Some(TrayEvent::DoubleClick),
            _ => None,
        };
        if let Some(m) = mapped {
            let _ = ev_tx.send(m);
        }
    }

    // Forward menu events.
    if let Ok(ev) = MenuEvent::receiver().try_recv() {
        let _ = ev_tx.send(TrayEvent::MenuItem {
            id: ev.id.as_ref().to_string(),
        });
    }
}

// ── StaticTray: sends commands to the main-thread pump ──────────────────

use std::sync::Arc;

struct StaticTray {
    cmd_tx: Sender<TrayCmd>,
    ev_rx: std::sync::Mutex<Receiver<TrayEvent>>,
    cfg: TrayConfig,
}

impl Tray for StaticTray {
    fn set_badge(&self, text: &str) -> TrayResult<()> {
        self.cmd_tx
            .send(TrayCmd::SetBadge { text: text.to_string() })
            .map_err(|e| TrayError::Backend(format!("tray channel closed: {e}")))
    }

    fn set_tooltip(&self, text: &str) -> TrayResult<()> {
        self.cmd_tx
            .send(TrayCmd::SetTooltip { text: text.to_string() })
            .map_err(|e| TrayError::Backend(format!("tray channel closed: {e}")))
    }

    fn notify(&self, _title: &str, _body: &str) -> TrayResult<()> {
        Ok(())
    }

    fn try_recv(&self) -> Option<TrayEvent> {
        self.ev_rx.lock().ok()?.try_recv().ok()
    }

    fn shutdown(&self) -> TrayResult<()> {
        let _ = self.cmd_tx.send(TrayCmd::Shutdown);
        Ok(())
    }

    fn backend_name(&self) -> &'static str {
        #[cfg(target_os = "macos")]
        { "nsstatusitem" }
        #[cfg(target_os = "windows")]
        { "shell_notifyicon" }
        #[cfg(target_os = "linux")]
        { "libappindicator" }
        #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
        { "unsupported" }
    }

    fn inbox_url(&self) -> Option<&str> {
        Some(&self.cfg.inbox_url)
    }
}

// ── Helpers ─────────────────────────────────────────────────────────────

fn make_placeholder_icon() -> TrayResult<Icon> {
    // Try to load branded tray icon from the app bundle's Resources directory.
    // Falls back to a programmatic 16x16 teal envelope if file not found.
    let resource_dirs = [
        std::path::PathBuf::from("/Applications/Phinbox.app/Contents/Resources"),
        // Also check relative to the running binary (development layout)
        std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|d| d.join("../Resources").canonicalize().unwrap_or_default()))
            .unwrap_or_default(),
    ];

    for dir in &resource_dirs {
        // Prefer @2x for Retina displays
        let path_2x = dir.join("tray_44.png");
        let path_1x = dir.join("tray_22.png");
        let path = if path_2x.exists() { &path_2x } else if path_1x.exists() { &path_1x } else { continue };
        if let Ok(img) = image::open(path) {
            let rgba = img.to_rgba8();
            let (w, h) = rgba.dimensions();
            return Icon::from_rgba(rgba.into_raw(), w, h)
                .map_err(|e| TrayError::Icon(e.to_string()));
        }
    }

    // Fallback: programmatic teal envelope (16x16, matches brand #7EBAB5)
    const SIZE: u32 = 16;
    let mut rgba = Vec::with_capacity((SIZE * SIZE * 4) as usize);
    for y in 0..SIZE {
        for x in 0..SIZE {
            let cx = x as f32 - 7.5;
            let cy = y as f32 - 7.5;
            // Envelope body: rounded rect from (2,4) to (13,12)
            let in_body = x >= 2 && x <= 13 && y >= 4 && y <= 12;
            // V-flap: lines from (2,4) to (7.5,8) to (13,4)
            let t_flap_l = ((y - 4) as f32 / 4.0).clamp(0.0, 1.0);
            let flap_l_x = 2.0 + t_flap_l * 5.5;
            let t_flap_r = ((y - 4) as f32 / 4.0).clamp(0.0, 1.0);
            let flap_r_x = 13.0 - t_flap_r * 5.5;
            let on_flap = in_body && y >= 4 && y <= 8
                && ((x as f32 - flap_l_x).abs() < 1.0 || (x as f32 - flap_r_x).abs() < 1.0);

            let (r, g, b, a) = if on_flap {
                (126u8, 186, 181, 255)  // #7EBAB5
            } else if in_body {
                // Check if near edge for outline effect
                let on_edge = x == 2 || x == 13 || y == 4 || y == 12;
                if on_edge {
                    (126u8, 186, 181, 255)  // teal outline
                } else {
                    (25u8, 35, 45, 255)  // dark fill
                }
            } else {
                (0, 0, 0, 0)  // transparent
            };
            rgba.extend_from_slice(&[r, g, b, a]);
        }
    }
    Icon::from_rgba(rgba, SIZE, SIZE).map_err(|e| TrayError::Icon(e.to_string()))
}

fn map_err<E: std::fmt::Display>(e: E) -> TrayError {
    TrayError::Backend(e.to_string())
}
