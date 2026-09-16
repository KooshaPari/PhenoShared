//! `phinbox daemon` subcommand implementation.

use std::path::PathBuf;

use phinbox::NotifyChannels;
use serde_json::json;

/// Run the inbox daemon in the foreground (server mode).
#[derive(Debug, clap::Args)]
pub struct DaemonArgs {
    /// Port to bind on (loopback only by default).
    #[arg(long, default_value_t = phinbox::inbox::daemon::DEFAULT_PORT)]
    pub port: u16,
    /// Bind address. Defaults to 127.0.0.1.
    #[arg(long, default_value = "127.0.0.1")]
    pub bind: String,
    /// iMessage destination (Apple ID).
    #[arg(long, env = "PHINBOX_IMESSAGE_TARGET")]
    pub imessage_target: Option<String>,
    /// Email destination.
    #[arg(long, env = "PHINBOX_EMAIL_TARGET")]
    pub email_target: Option<String>,
    /// Webhook URL.
    #[arg(long, env = "PHINBOX_WEBHOOK_URL")]
    pub webhook_url: Option<String>,
    /// Fire an OS-native notification (Notification Center / Toast).
    #[arg(long, env = "PHINBOX_NOTIFY_NATIVE")]
    pub native: bool,
    /// Disable the OS tray icon even if the `tray-native` feature is on.
    #[arg(long)]
    pub no_tray: bool,
    /// Force-enable the tray even when running in a context where
    /// `build_tray` would otherwise skip the native backend.
    #[arg(long, hide = true)]
    pub force_tray: bool,
    /// Open the inbox index in the default browser once the daemon is ready.
    #[arg(long, env = "PHINBOX_AUTO_OPEN_BROWSER")]
    pub auto_open_browser: bool,
}

pub fn cmd_daemon(args: DaemonArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    let bind: std::net::IpAddr = args
        .bind
        .parse()
        .map_err(|e| format!("invalid --bind '{}': {e}", args.bind))?;
    let notify = NotifyChannels {
        imessage_target: args.imessage_target,
        email_target: args.email_target,
        webhook_url: args.webhook_url,
        native: args.native,
    };
    let cfg = phinbox::inbox::daemon::DaemonConfig {
        inbox_root: inbox_dir.clone(),
        port: args.port,
        bind,
        notify,
        enable_tray: !args.no_tray,
    };
    let handle = phinbox::inbox::daemon::start_daemon(cfg).map_err(|e| e.to_string())?;
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "status": "started",
            "port": handle.port,
            "bind": handle.bind_addr.to_string(),
            "inbox_root": handle.inbox_root,
            "open_url": super::open_url_from_handle(&handle),
            "open_url_format": phinbox::inbox_open_url_for("<id>"),
        }))
        .unwrap()
    );
    if args.auto_open_browser {
        let url = super::open_url_from_handle(&handle);
        match phinbox::open_in_default_browser(&url) {
            Ok(()) => eprintln!("auto-opened {url} in default browser"),
            Err(e) => eprintln!("auto-open failed: {e}"),
        }
    }
    let shutdown = daemon_shutdown_signal();
    block_on(shutdown);
    let _ = handle.stop();
    Ok(())
}

fn daemon_shutdown_signal() -> impl std::future::Future<Output = ()> + Send + 'static {
    use std::sync::{Arc, Condvar, Mutex};
    let state = Arc::new((Mutex::new(false), Condvar::new()));
    let state_for_thread = state.clone();
    std::thread::spawn(move || {
        wait_for_termination();
        let (lock, cv) = &*state_for_thread;
        *lock.lock().unwrap() = true;
        cv.notify_all();
    });
    async move {
        let (lock, cv) = &*state;
        let mut signaled = lock.lock().unwrap();
        while !*signaled {
            signaled = cv.wait(signaled).unwrap();
        }
    }
}

fn block_on<F: std::future::Future<Output = ()>>(fut: F) {
    use std::sync::Arc;
    use std::task::{Context, Poll, Wake, Waker};
    struct ParkOnce;
    impl Wake for ParkOnce {
        fn wake(self: Arc<Self>) {}
        fn wake_by_ref(self: &Arc<Self>) {}
    }
    let waker = Waker::from(Arc::new(ParkOnce));
    let mut cx = Context::from_waker(&waker);
    let mut fut = Box::pin(fut);
    loop {
        if let Poll::Ready(()) = fut.as_mut().poll(&mut cx) {
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
}

#[cfg(unix)]
#[allow(unsafe_code)]
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

#[cfg(not(unix))]
#[allow(unsafe_code)]
fn wait_for_termination() {
    extern "system" {
        fn SetConsoleCtrlHandler(
            handler: Option<extern "system" fn(u32) -> i32>,
            add: i32,
        ) -> i32;
    }
    extern "system" fn handler(_typ: u32) -> i32 {
        std::process::exit(0);
    }
    unsafe {
        SetConsoleCtrlHandler(Some(handler), 1);
    }
    loop {
        std::thread::park();
    }
}
