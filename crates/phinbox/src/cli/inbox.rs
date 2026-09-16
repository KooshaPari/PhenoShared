//! `phinbox inbox` subcommand implementation.

use std::path::PathBuf;

/// Inspect the inbox: list pending, show one in detail, or open the UI.
#[derive(Debug, clap::Args)]
pub struct InboxArgs {
    /// List all pending requests (default if no other arg).
    #[arg(long, conflicts_with_all = &["show", "open"])]
    pub list: bool,
    /// Show full JSON for a single request.
    #[arg(long)]
    pub show: Option<String>,
    /// Print the open-the-form URL for a single request without opening.
    #[arg(long, conflicts_with_all = &["list", "show"])]
    pub url: Option<String>,
    /// Open the inbox UI in the default browser.
    #[arg(long, conflicts_with_all = &["list", "show", "url"])]
    pub open: bool,
    /// Clean up expired / completed entries older than the given number of seconds.
    #[arg(long)]
    pub gc_age_secs: Option<u64>,
    /// Launch the terminal-UI inbox viewer.
    #[arg(long, conflicts_with_all = &["list", "show", "url", "open", "gc_age_secs"])]
    pub tui: bool,
    /// In TUI mode, live-follow changes via the inbox change bus.
    #[arg(long)]
    pub follow: bool,
}

pub fn cmd_inbox(args: InboxArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    // TUI viewer
    if args.tui {
        match phinbox::tui_run(inbox_dir, args.follow) {
            Ok(phinbox::TuiOutcome::Quit | phinbox::TuiOutcome::Answered(_) |
phinbox::TuiOutcome::Dismissed(_)) => return Ok(()),
            Ok(phinbox::TuiOutcome::NoTty) => {
                let count = phinbox::tui_render_plain(inbox_dir)?;
                eprintln!(
                    "(running plain-text fallback — {count} pending request(s); \
                     run on a real terminal for the full split-pane UI)"
                );
                return Ok(());
            }
            Err(e) => return Err(e),
        }
    }
    if let Some(id) = args.url {
        let url = phinbox::inbox_open_url_for(&id);
        println!("{url}");
        return Ok(());
    }
    if let Some(id) = args.show {
        let req = phinbox::inbox::load(inbox_dir, &id).map_err(|e| e.to_string())?;
        println!(
            "{}",
            serde_json::to_string_pretty(&req).map_err(|e| e.to_string())?
        );
        return Ok(());
    }
    if args.open {
        let base = phinbox::inbox_live_url(inbox_dir, None)
            .unwrap_or_else(|| format!("http://127.0.0.1:{}", phinbox::INBOX_DEFAULT_PORT));
        let url = format!("{base}/inbox");
        println!("{url}");
        let _ = std::process::Command::new(open_cmd())
            .args(open_args(&url))
            .status();
        return Ok(());
    }
    if let Some(age_secs) = args.gc_age_secs {
        let now = phinbox::inbox::unix_now_ms();
        let mut removed = 0usize;
        for dir in [
            phinbox::inbox::inbox_pending_dir(inbox_dir),
            phinbox::inbox::answered_dir(inbox_dir),
        ] {
            if !dir.exists() {
                continue;
            }
            for entry in std::fs::read_dir(&dir).map_err(|e| e.to_string())? {
                let entry = entry.map_err(|e| e.to_string())?;
                let meta = entry.metadata().map_err(|e| e.to_string())?;
                let mtime = meta
                    .modified()
                    .ok()
                    .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                    .map_or(0, |d| d.as_millis() as u64);
                if now.saturating_sub(mtime) > age_secs * 1000 {
                    std::fs::remove_file(entry.path()).ok();
                    removed += 1;
                }
            }
        }
        println!("{{\"removed\": {removed}}}");
        return Ok(());
    }
    // Default: --list
    let reqs = phinbox::inbox::list_pending(inbox_dir).map_err(|e| e.to_string())?;
    let summaries: Vec<_> = reqs.iter().map(phinbox::views::render_summary_json).collect();
    println!(
        "{}",
        serde_json::to_string(&summaries).map_err(|e| e.to_string())?
    );
    Ok(())
}

pub(crate) fn open_cmd() -> &'static str {
    if cfg!(target_os = "macos") {
        "open"
    } else if cfg!(target_os = "windows") {
        "cmd"
    } else {
        "xdg-open"
    }
}

pub(crate) fn open_args(url: &str) -> Vec<String> {
    if cfg!(target_os = "macos") {
        vec![url.to_string()]
    } else if cfg!(target_os = "windows") {
        vec!["/c".into(), "start".into(), String::new(), url.to_string()]
    } else {
        vec![url.to_string()]
    }
}
