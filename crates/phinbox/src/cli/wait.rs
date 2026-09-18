//! `phinbox wait` subcommand implementation.
//!
//! Exit contract (matches `phinbox validate` and the crate's MCP surface):
//! the typed response envelope always goes to stdout, and the process exits
//! non-zero when that envelope is a *failure*. `ElicitResponse::Failed` and
//! `ElicitResponse::TimedOut` are errors elsewhere in this crate — the MCP
//! tool flags exactly those two as `isError` — so a wait that resolved
//! without an answer (cancelled is a legitimate outcome; expired/timeout is
//! not) must not look like success to a caller that only checks the status.

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
    let request_id = req.request_id.clone();
    let state = req.state;
    let out = match req.response {
        Some(r) => r,
        None => ElicitResponse::Failed {
            reason: format!("request {request_id} reached state {state:?} without a response"),
        },
    };
    println!(
        "{}",
        serde_json::to_string_pretty(&out).map_err(|e| e.to_string())?
    );
    if matches!(
        out,
        ElicitResponse::Failed { .. } | ElicitResponse::TimedOut { .. }
    ) {
        return Err(format!(
            "request {request_id} resolved to {state:?} without an answer \
             (failure envelope above)"
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use phinbox::inbox::{enqueue, RequestOrigin, RequestState};
    use phinbox::spec::{FieldSpec, FieldValue, PromptSpec, Urgency};
    use std::time::Instant;

    fn spec(id: &str) -> PromptSpec {
        PromptSpec {
            details: None,
            title: "Probe".into(),
            question: "?".into(),
            field: FieldSpec::Boolean {
                label: "Approve?".into(),
                default: None,
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Info,
            timeout_secs: 60,
            request_id: Some(id.into()),
        }
    }

    fn origin() -> RequestOrigin {
        RequestOrigin {
            hostname: "h".into(),
            process: "p".into(),
            pid: 1,
            callback: None,
        }
    }

    fn wait_args(id: &str, timeout_secs: u64) -> WaitArgs {
        WaitArgs {
            request_id: id.into(),
            timeout_secs,
            poll_interval_ms: 10,
        }
    }

    /// A terminal-without-response request must not look like success to a
    /// caller that only checks the exit status: the envelope is `failed`, so
    /// `cmd_wait` returns `Err` (which `main` turns into a non-zero exit).
    ///
    /// The request expired with no daemon running, so this also pins that the
    /// wait settles the TTL itself instead of blocking until its own timeout.
    #[test]
    fn wait_on_expired_request_fails_instead_of_reporting_success() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path().to_path_buf();
        let mut req = phinbox::inbox::PendingRequest::new(spec("stale-wait"), origin());
        req.expires_at_ms = 1;
        enqueue(&root, &req).unwrap();

        let t0 = Instant::now();
        let err = cmd_wait(wait_args("stale-wait", 30), &root).unwrap_err();
        let elapsed = t0.elapsed();
        assert!(
            err.contains("without an answer"),
            "failure must be reported as an error: {err}"
        );
        assert!(
            elapsed < Duration::from_secs(5),
            "the expiry must settle the wait, not the 30s overall timeout (took {elapsed:?})"
        );
        assert_eq!(
            phinbox::inbox::load(&root, "stale-wait").unwrap().state,
            RequestState::Expired
        );
    }

    /// Control: a normal answer is still a success (exit 0).
    #[test]
    fn wait_on_answered_request_succeeds() {
        let tmp = tempfile::tempdir().unwrap();
        let root = tmp.path().to_path_buf();
        let req = phinbox::inbox::PendingRequest::new(spec("ok-wait"), origin());
        enqueue(&root, &req).unwrap();

        let mut answered = req.clone();
        answered.state = RequestState::Answered;
        answered.response = Some(ElicitResponse::Answered {
            value: FieldValue::Boolean(true),
            notes: None,
        });
        phinbox::inbox::finalize(&root, &answered).unwrap();

        cmd_wait(wait_args("ok-wait", 5), &root).unwrap();
    }
}
