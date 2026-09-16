//! `phinbox ask` subcommand implementation.

use std::path::PathBuf;

use phinbox::inbox::RequestOrigin;
use phinbox::options::RendererPreference;
use phinbox::spec::PromptSpec;
use serde_json::json;

/// Render a popup (blocking) or queue it (with `--async`).
#[derive(Debug, clap::Args)]
pub struct AskArgs {
    #[arg(long)]
    pub title: Option<String>,
    #[arg(long)]
    pub question: Option<String>,

    /// Render from an inline JSON spec.
    #[arg(long, conflicts_with_all = &["title", "question"])]
    pub from_json: Option<String>,

    /// Render from a JSON spec file.
    #[arg(long, conflicts_with_all = &["title", "question"])]
    pub from_file: Option<PathBuf>,

    /// Don't block — queue the prompt in the inbox and print the
    /// `request_id` as JSON immediately.
    #[arg(long)]
    pub r#async: bool,

    /// Notification targets (comma-separated) for the `--async` workflow.
    #[arg(long, env = "PHINBOX_NOTIFY")]
    pub notify: Option<String>,

    /// Urgency: info | warning | error | secret.
    #[arg(long, default_value = "info")]
    pub urgency: String,

    /// Timeout in seconds. 0 = no timeout.
    #[arg(long, default_value = "600")]
    pub timeout_secs: u32,

    /// Cancel button label.
    #[arg(long, default_value = "Cancel")]
    pub cancel_label: Option<String>,

    /// Confirm button label.
    #[arg(long, default_value = "OK")]
    pub confirm_label: Option<String>,
}

pub fn cmd_ask(
    args: AskArgs,
    renderer: Option<RendererPreference>,
    inbox_dir: &PathBuf,
) -> Result<(), String> {
    let spec = if let Some(json_str) = args.from_json {
        serde_json::from_str::<PromptSpec>(&json_str)
            .map_err(|e| format!("invalid --from-json: {e}"))?
    } else if let Some(path) = args.from_file {
        let text = std::fs::read_to_string(&path)
            .map_err(|e| format!("read {}: {e}", path.display()))?;
        serde_json::from_str::<PromptSpec>(&text)
            .map_err(|e| format!("parse {}: {e}", path.display()))?
    } else {
        super::common::build_minimal_spec_from_flags(&args)?
    };

    if args.r#async {
        let origin = RequestOrigin {
            hostname: super::common::hostname(),
            process: std::env::current_exe()
                .ok()
                .and_then(|p| p.file_name().map(|n| n.to_string_lossy().into_owned()))
                .unwrap_or_else(|| "phinbox".into()),
            pid: std::process::id(),
            callback: None,
        };
        let req = phinbox::PendingRequest::new(spec, origin);
        let path = phinbox::inbox::enqueue(inbox_dir, &req).map_err(|e| e.to_string())?;
        let out = json!({
            "status": "queued",
            "request_id": req.request_id,
            "path": path,
            "open_url": phinbox::inbox_open_url_for(&req.request_id),
            "wait": format!("phinbox wait --request-id {}", req.request_id),
        });
        println!("{}", serde_json::to_string_pretty(&out).unwrap());

        // Fire notifications (best-effort).
        let cfg = super::common::parse_notify_cfg(args.notify.as_deref());
        if cfg != phinbox::NotifyChannels::default() {
            let attempts = phinbox::inbox::notify::surface_all(&req, &cfg);
            let summary: Vec<_> = attempts
                .iter()
                .map(|a| {
                    serde_json::json!({
                        "kind": format!("{:?}", a.kind),
                        "ok": a.ok,
                        "detail": a.detail,
                    })
                })
                .collect();
            eprintln!(
                "notify: {}",
                serde_json::to_string(&summary).unwrap_or_default()
            );
        }
        return Ok(());
    }

    let mut opts = phinbox::ElicitOptions::default();
    if let Some(r) = renderer {
        opts.renderer = r;
    }
    let response = phinbox::elicit_with(&spec, &opts).map_err(|e| e.to_string())?;
    let out =
        serde_json::to_string_pretty(&response).map_err(|e| format!("serialize response: {e}"))?;
    println!("{out}");
    Ok(())
}
