//! Inbox daemon — long-running process that:
//! 1. Serves the HTML inbox UI on `http://127.0.0.1:7117/inbox/<id>`.
//! 2. Receives `POST /answer/<id>` from the HTML form and persists the
//!    answer to `answered/` so the agent's `phinbox wait` returns.
//! 3. Polls the inbox directory and surfaces new requests via the
//!    configured `NotifyChannels` (tray, iMessage, email, webhook).
//!
//! The daemon is **single-host, single-user** — there is exactly one
//! inbox per machine, identified by the resolved `default_inbox_root()`.
//! It is **idempotent** at startup: if a daemon is already running on
//! the same inbox root and port, the second invocation is a no-op.
//!
//! HTTP backend is deliberately minimal: `tiny_http`-style blocking
//! socket-per-thread. There is no router, no async runtime, no TLS —
//! the inbox is local-only and binds to `127.0.0.1` only.

pub(crate) mod form;
pub(crate) mod http;
pub mod lockfile;
pub mod notifier;

use std::net::{IpAddr, SocketAddr, TcpListener};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;

use crate::error::ElicitError;
use crate::inbox::notify::NotifyChannels;
use crate::tray::{build_tray, Tray, TrayConfig};
use tracing::{info, warn};

pub use lockfile::{live_url, read_lockfile, LockfilePayload};

/// Default port the daemon listens on.
pub const DEFAULT_PORT: u16 = 7117;

/// Bundle of handles returned from `start_daemon` — gives callers the
/// port, inbox root, and a shutdown signal they can flip to terminate
/// the daemon cleanly.
#[derive(Debug)]
pub struct DaemonHandle {
    pub port: u16,
    pub inbox_root: PathBuf,
    pub bind_addr: IpAddr,
    pub lockfile: PathBuf,
    pub shutdown: Arc<AtomicBool>,
}

impl DaemonHandle {
    /// Signal the daemon to exit and wait for it to drop its lockfile.
    pub fn stop(&self) -> std::io::Result<()> {
        self.shutdown.store(true, Ordering::SeqCst);
        // The daemon watches `daemon.lock` for mtime changes; we touch it
        // once to wake its select/poll loop immediately.
        std::fs::File::options()
            .write(true)
            .truncate(true)
            .open(&self.lockfile)?;
        Ok(())
    }
}

/// Configuration knobs the CLI forwards when launching the daemon.
#[derive(Debug, Clone)]
pub struct DaemonConfig {
    pub inbox_root: PathBuf,
    pub port: u16,
    pub bind: IpAddr,
    pub notify: NotifyChannels,
    /// If true, attempt to register a tray icon. If `tray-native` is not
    /// compiled in or the OS rejects the registration, the tray is
    /// silently a no-op.
    pub enable_tray: bool,
}

/// Boot the daemon. Returns a handle the caller can use to shut it
/// down. The function spawns the HTTP server + notifier in background
/// threads and returns immediately.
pub fn start_daemon(cfg: DaemonConfig) -> Result<DaemonHandle, ElicitError> {
    std::fs::create_dir_all(&cfg.inbox_root)?;

    // Detect an existing daemon and short-circuit if we're already
    // running on the same port + root.
    if let Some(existing) = lockfile::read_lockfile(&cfg.inbox_root) {
        if existing.root == cfg.inbox_root
            && existing.port == cfg.port
            && existing.bind == cfg.bind
        {
            // Verify it's actually live; if not, remove the stale lock.
            if lockfile::is_port_live(cfg.bind, cfg.port) {
                return Err(ElicitError::RendererFailed(format!(
                    "phinbox inbox daemon already running on {}:{}",
                    cfg.bind, cfg.port
                )));
            }
            let _ = std::fs::remove_file(
                cfg.inbox_root.join(lockfile::LOCKFILE_NAME),
            );
        }
    }

    let bind_addr = SocketAddr::new(cfg.bind, cfg.port);
    let listener = TcpListener::bind(bind_addr).map_err(|e| {
        ElicitError::RendererFailed(format!("bind {bind_addr}: {e}"))
    })?;
    // The default accept is blocking. Use non-blocking so the wakeup
    // loop can poll `shutdown` frequently without a separate timer thread.
    listener
        .set_nonblocking(true)
        .map_err(|e| ElicitError::RendererFailed(format!("set_nonblocking: {e}")))?;
    let actual_port = listener
        .local_addr()
        .map_err(|e| ElicitError::RendererFailed(format!("local_addr: {e}")))?
        .port();

    let shutdown = Arc::new(AtomicBool::new(false));
    let lockfile = cfg.inbox_root.join(lockfile::LOCKFILE_NAME);
    lockfile::write_lockfile(&lockfile, &cfg.inbox_root, actual_port, cfg.bind, None)?;

    let tray_url = format!("http://{}:{}", cfg.bind, actual_port);
    // ---- tray icon (best-effort, never blocks boot) ---------------
    let tray: Arc<dyn Tray> = if cfg.enable_tray {
        let tray_cfg = TrayConfig::new(tray_url.clone(), cfg.inbox_root.clone());
        match build_tray(tray_cfg) {
            Ok(t) => {
                info!(backend = t.backend_name(), "tray icon attached");
                t
            }
            Err(e) => {
                warn!(error = %e, "tray attach failed; daemon will run without tray");
                build_tray(TrayConfig::new(
                    tray_url.clone(),
                    cfg.inbox_root.clone(),
                ))
                .unwrap()
            }
        }
    } else {
        build_tray(TrayConfig::new(tray_url.clone(), cfg.inbox_root.clone())).unwrap()
    };

    // ---- worker 1: HTTP server ------------------------------------
    {
        let shutdown = Arc::clone(&shutdown);
        let inbox_root = cfg.inbox_root.clone();
        let lockfile = lockfile.clone();
        thread::Builder::new()
            .name("phinbox-http".into())
            .spawn(move || {
                if let Err(e) = http::run_http_loop(listener, &inbox_root, &shutdown) {
                    warn!(error = %e, "http loop exited");
                }
                let _ = std::fs::remove_file(&lockfile);
            })?;
    }

    // ---- worker 2: notifier poller --------------------------------
    {
        let shutdown = Arc::clone(&shutdown);
        let inbox_root = cfg.inbox_root.clone();
        let notify = cfg.notify.clone();
        let tray_for_badge = Arc::clone(&tray);
        thread::Builder::new()
            .name("phinbox-notify".into())
            .spawn(move || {
                notifier::run_notifier_loop(
                    &inbox_root,
                    notify,
                    &shutdown,
                    Some(tray_for_badge),
                );
            })?;
    }

    // ---- worker 3: tray event pump --------------------------------
    {
        let shutdown = Arc::clone(&shutdown);
        let fallback_url = tray_url.clone();
        thread::Builder::new()
            .name("phinbox-tray".into())
            .spawn(move || {
                notifier::run_tray_loop(tray.as_ref(), &shutdown, &fallback_url);
            })?;
    }

    info!(
        port = actual_port,
        bind = %cfg.bind,
        inbox = %cfg.inbox_root.display(),
        "phinbox inbox daemon started"
    );

    Ok(DaemonHandle {
        port: actual_port,
        inbox_root: cfg.inbox_root,
        bind_addr: cfg.bind,
        lockfile,
        shutdown,
    })
}

#[cfg(test)]
mod tests;
