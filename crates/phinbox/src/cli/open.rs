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
    Some(phinbox::inbox_open_url_for(&newest.request_id))
        .map(|u| u.replace("127.0.0.1", &base_url_host(base)))
}

fn base_url_host(base: &str) -> String {
    base.trim_start_matches("http://")
        .split('/')
        .next()
        .unwrap_or("127.0.0.1")
        .to_string()
}

#[allow(unsafe_code)]
#[cfg(unix)]
unsafe fn libc_setsid() -> i32 {
    extern "C" {
        fn setsid() -> i32;
    }
    setsid()
}
