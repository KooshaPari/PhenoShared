//! `phinbox open` subcommand implementation.

use std::path::PathBuf;

/// Open the inbox in the default browser.
#[derive(Debug, clap::Args)]
pub struct OpenArgs {
    /// Deep-link to the most recent pending request instead of the index page.
    #[arg(long)]
    pub latest: bool,
    /// Print the URL without opening the browser.
    #[arg(long)]
    pub print_only: bool,
    /// If no daemon is running, spawn one in the background first.
    #[arg(long)]
    pub spawn_if_missing: bool,
}

#[allow(unsafe_code)]
pub fn cmd_open(args: OpenArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    use std::process::Command;

    let mut base = phinbox::inbox_live_url(inbox_dir, None);

    // Optionally spawn a daemon if nothing is running.
    if base.is_none() && args.spawn_if_missing {
        eprintln!(
            "(no inbox daemon running — spawning one in the background; \
             set --inbox-dir to control the data location)"
        );
        let exe = std::env::current_exe().map_err(|e| e.to_string())?;
        let mut cmd = Command::new(exe);
        cmd.arg("daemon");
        if inbox_dir != &phinbox::inbox::default_inbox_root() {
            cmd.arg("--inbox-dir").arg(inbox_dir);
        }
        #[cfg(unix)]
        {
            use std::os::unix::process::CommandExt;
            unsafe {
                cmd.pre_exec(|| {
                    libc_setsid();
                    Ok(())
                });
            }
        }
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const DETACHED_PROCESS: u32 = 0x00000008;
            cmd.creation_flags(DETACHED_PROCESS);
        }
        cmd.stdin(std::process::Stdio::null())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .map_err(|e| format!("failed to spawn daemon: {e}"))?;

        // Wait up to 5s for the daemon to write its lockfile + bind.
        for _ in 0..50 {
            std::thread::sleep(std::time::Duration::from_millis(100));
            if let Some(u) = phinbox::inbox_live_url(inbox_dir, None) {
                base = Some(u);
                break;
            }
        }
    }

    let base = base.unwrap_or_else(|| {
        format!("http://127.0.0.1:{}", phinbox::INBOX_DEFAULT_PORT)
    });

    let url = if args.latest {
        match latest_pending_form_url(inbox_dir, &base) {
            Some(u) => u,
            None => format!("{base}/inbox"),
        }
    } else {
        format!("{base}/inbox")
    };

    println!("{url}");

    if !args.print_only {
        let _ = Command::new(super::inbox::open_cmd())
            .args(super::inbox::open_args(&url))
            .status();
    }
    Ok(())
}

fn latest_pending_form_url(inbox_dir: &PathBuf, base: &str) -> Option<String> {
    let reqs = phinbox::inbox_list_pending(inbox_dir).ok()?;
    let newest = reqs
        .into_iter()
        .max_by_key(|r| r.queued_at_ms)?;
    // Build from the live base so the daemon's host *and* port are kept.
    // Patching a URL that was constructed from a different base threw the
    // live port away (and duplicated it when `PHINBOX_BASE_URL` was set).
    Some(phinbox::inbox::notify::inbox_open_url_with_base(
        base,
        &newest.request_id,
    ))
}

#[allow(unsafe_code)]
#[cfg(unix)]
unsafe fn libc_setsid() -> i32 {
    extern "C" {
        fn setsid() -> i32;
    }
    setsid()
}

// ---- tests ----------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use phinbox::inbox::{RequestOrigin, RequestState};
    use phinbox::PromptSpec;

    fn spec_with_id(request_id: &str) -> PromptSpec {
        PromptSpec {
            details: None,
            title: "t".into(),
            question: "q".into(),
            field: phinbox::FieldSpec::Boolean {
                label: "?".into(),
                default: Some(true),
            },
            notes: None,
            buttons: None,
            urgency: phinbox::Urgency::Info,
            timeout_secs: 600,
            request_id: Some(request_id.into()),
        }
    }

    fn enqueue(root: &std::path::Path, request_id: &str, queued_at_ms: u64) {
        let origin = RequestOrigin {
            hostname: "h".into(),
            process: "p".into(),
            pid: 1,
            callback: None,
        };
        let mut req = phinbox::PendingRequest::new(spec_with_id(request_id), origin);
        req.queued_at_ms = queued_at_ms;
        req.state = RequestState::Pending;
        phinbox::inbox::enqueue(root, &req).expect("enqueue");
    }

    #[test]
    fn latest_url_uses_live_base_host_and_port() {
        let dir = tempfile::tempdir().unwrap();
        enqueue(dir.path(), "req-1", 1_000);
        let url = latest_pending_form_url(&dir.path().to_path_buf(), "http://127.0.0.1:7412")
            .expect("a pending request");
        // Regression: the old host-patching path always produced
        // `http://localhost:7117/...` because the literal `127.0.0.1`
        // never appears in the default `localhost` base.
        assert_eq!(url, "http://127.0.0.1:7412/inbox/req-1");
    }

    #[test]
    fn latest_url_picks_newest_and_keeps_trailing_slash_base_clean() {
        let dir = tempfile::tempdir().unwrap();
        enqueue(dir.path(), "old", 1_000);
        enqueue(dir.path(), "new", 2_000);
        let url = latest_pending_form_url(&dir.path().to_path_buf(), "http://127.0.0.1:7412/")
            .expect("a pending request");
        assert_eq!(url, "http://127.0.0.1:7412/inbox/new");
    }

    #[test]
    fn latest_url_does_not_rewrite_request_id() {
        let dir = tempfile::tempdir().unwrap();
        enqueue(dir.path(), "127.0.0.1-x", 1_000);
        let url = latest_pending_form_url(&dir.path().to_path_buf(), "http://127.0.0.1:7412")
            .expect("a pending request");
        assert_eq!(url, "http://127.0.0.1:7412/inbox/127.0.0.1-x");
    }

    #[test]
    fn latest_url_is_none_when_nothing_pending() {
        let dir = tempfile::tempdir().unwrap();
        assert!(
            latest_pending_form_url(&dir.path().to_path_buf(), "http://127.0.0.1:7412").is_none()
        );
    }
}
