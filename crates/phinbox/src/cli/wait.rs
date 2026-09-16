//! `phinbox wait` subcommand implementation.

use std::path::PathBuf;
use std::time::Duration;

use phinbox::spec::ElicitResponse;

/// Block until a queued `--async` request has been answered (or times out).
#[derive(Debug, clap::Args)]
pub struct WaitArgs {
    /// The request ID to wait for.
    #[arg(long)]
    pub request_id: String,
    /// Timeout in seconds. 0 = wait forever.
    #[arg(long, default_value_t = 600)]
    pub timeout_secs: u64,
    /// Poll interval in milliseconds.
    #[arg(long, default_value_t = 200)]
    pub poll_interval_ms: u64,
}

pub fn cmd_wait(args: WaitArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    let poll = Duration::from_millis(args.poll_interval_ms);
    let overall = if args.timeout_secs == 0 {
        Duration::from_secs(60 * 60 * 24 * 365) // ~1 year
    } else {
        Duration::from_secs(args.timeout_secs)
    };
    let req = phinbox::wait_for_response(inbox_dir, &args.request_id, poll, overall)
        .map_err(|e| e.to_string())?;
    let out = match req.response {
        Some(r) => r,
        None => ElicitResponse::Failed {
            reason: format!(
                "request {} reached state {:?} without a response",
                req.request_id, req.state
            ),
        },
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&out).map_err(|e| e.to_string())?
    );
    Ok(())
}
