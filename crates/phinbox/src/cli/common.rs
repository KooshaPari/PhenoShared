//! Shared CLI types and utilities for the phinbox binary.

use phinbox::spec::{
    ButtonSpec, ElicitResponse, FieldSpec, FieldValue, NotesSpec, PromptSpec, Urgency,
};
use phinbox::options::RendererPreference;
use serde_json::json;

// ---- args ----

#[derive(Debug, clap::Args)]
pub struct SchemaArgs {
    /// Print the `FieldSpec` schema instead.
    #[arg(long)]
    pub field: bool,
    /// Print the `ElicitResponse` schema instead.
    #[arg(long)]
    pub response: bool,
}

#[derive(Debug, clap::Args)]
pub struct SmokeArgs {
    /// Title to use for the smoke popup.
    #[arg(long, default_value = "phinbox smoke test")]
    pub title: String,
    /// Skip the popup entirely (just verify CLI parsing).
    #[arg(long)]
    pub no_render: bool,
}

// ---- commands ----

pub fn cmd_schema(args: SchemaArgs) {
    let s = if args.field {
        serde_json::to_string_pretty(&schemars::schema_for!(FieldSpec)).unwrap()
    } else if args.response {
        phinbox::schema_response_json().to_string()
    } else {
        phinbox::schema_json().to_string()
    };
    println!("{s}");
}

pub fn cmd_detect() {
    let platform = phinbox::platform();
    let auto = phinbox::detect_renderer(RendererPreference::AutoGui);
    let forced_tty = phinbox::detect_renderer(RendererPreference::ForceTty);
    let forced_gui = phinbox::detect_renderer(RendererPreference::ForceGui);
    let inbox_root = phinbox::inbox::default_inbox_root();
    let result = json!({
        "platform": platform,
        "renderer_auto": auto,
        "renderer_force_tty": forced_tty,
        "renderer_force_gui": forced_gui,
        "inbox_root": inbox_root,
    });
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}

pub fn cmd_smoke(args: SmokeArgs, renderer: Option<RendererPreference>) -> Result<(), String> {
    if args.no_render {
        println!("smoke: --no-render set, skipping popup");
        return Ok(());
    }
    let spec = PromptSpec {
        title: args.title,
        question: "This is the phinbox smoke test. Did it work?".into(),
        field: FieldSpec::Boolean {
            label: "Worked?".into(),
            default: Some(true),
        },
        notes: None,
        buttons: None,
        urgency: Urgency::Info,
        timeout_secs: 30,
        request_id: Some("smoke".into()),
    };
    let mut opts = phinbox::ElicitOptions::default();
    if let Some(r) = renderer {
        opts.renderer = r;
    }
    match phinbox::elicit_with(&spec, &opts) {
        Ok(ElicitResponse::Answered {
            value: FieldValue::Boolean(b),
            ..
        }) => {
            if b {
                println!("smoke: passed");
                Ok(())
            } else {
                println!("smoke: user said no");
                Err("user reported failure".into())
            }
        }
        Ok(ElicitResponse::Cancelled { .. }) => Err("user cancelled".into()),
        Ok(ElicitResponse::TimedOut { .. }) => Err("popup timed out".into()),
        Ok(ElicitResponse::Failed { reason }) => Err(format!("popup failed: {reason}")),
        Ok(other) => Err(format!("unexpected response variant: {other:?}")),
        Err(e) => Err(e.to_string()),
    }
}

// ---- utilities ----

pub fn init_tracing(verbose: u8) {
    use tracing_subscriber::EnvFilter;
    let level = match verbose {
        0 => "warn",
        1 => "info",
        2 => "debug",
        _ => "trace",
    };
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new(level));
    let _ = tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_target(false)
        .try_init();
}

pub fn hostname() -> String {
    std::env::var("HOSTNAME")
        .or_else(|_| std::env::var("COMPUTERNAME"))
        .unwrap_or_else(|_| {
            std::fs::read_to_string("/etc/hostname")
                .ok().map_or_else(|| "unknown".to_string(), |s| s.trim().to_string())
        })
}

pub fn build_minimal_spec_from_flags(args: &super::ask::AskArgs) -> Result<PromptSpec, String> {
    let title = args
        .title
        .clone()
        .ok_or_else(|| "--title is required (or use --from-json / --from-file / --async)".to_string())?;
    let question = args
        .question
        .clone()
        .ok_or_else(|| {
            "--question is required (or use --from-json / --from-file / --async)".to_string()
        })?;
    let urgency = match args.urgency.as_str() {
        "info" => Urgency::Info,
        "warning" => Urgency::Warning,
        "error" => Urgency::Error,
        "secret" => Urgency::Secret,
        other => return Err(format!("invalid urgency '{other}'")),
    };
    let buttons = if args.cancel_label.is_some() || args.confirm_label.is_some() {
        Some(ButtonSpec {
            cancel: args.cancel_label.clone().unwrap_or_else(|| "Cancel".into()),
            confirm: args.confirm_label.clone().unwrap_or_else(|| "OK".into()),
            default_is_cancel: false,
        })
    } else {
        None
    };
    Ok(PromptSpec {
        title,
        question,
        field: FieldSpec::Text {
            label: "Enter value".into(),
            default: None,
            placeholder: None,
            max_length: None,
            secret: matches!(urgency, Urgency::Secret),
            pattern: None,
        },
        notes: Some(NotesSpec {
            label: "Notes (optional)".into(),
            default: None,
            max_length: None,
            required: false,
        }),
        buttons,
        urgency,
        timeout_secs: args.timeout_secs,
        request_id: None,
    })
}

pub fn parse_notify_cfg(spec: Option<&str>) -> phinbox::NotifyChannels {
    let mut cfg = phinbox::NotifyChannels::default();
    let Some(spec) = spec else { return cfg };
    for piece in spec.split(',').filter(|s| !s.trim().is_empty()) {
        let piece = piece.trim();
        if piece == "native" {
            cfg.native = true;
            continue;
        }
        if let Some(rest) = piece.strip_prefix("imessage:") {
            cfg.imessage_target = Some(rest.to_string());
            continue;
        }
        if let Some(rest) = piece.strip_prefix("email:") {
            cfg.email_target = Some(rest.to_string());
            continue;
        }
        if let Some(rest) = piece.strip_prefix("webhook:") {
            cfg.webhook_url = Some(rest.to_string());
            continue;
        }
    }
    cfg
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ask::AskArgs;

    #[test]
    fn build_minimal_spec_uses_defaults() {
        let args = AskArgs {
            title: Some("t".into()),
            question: Some("q".into()),
            from_json: None,
            from_file: None,
            r#async: false,
            notify: None,
            urgency: "warning".into(),
            timeout_secs: 60,
            cancel_label: None,
            confirm_label: None,
        };
        let spec = build_minimal_spec_from_flags(&args).unwrap();
        assert_eq!(spec.title, "t");
        assert_eq!(spec.question, "q");
        assert_eq!(spec.urgency, Urgency::Warning);
        assert_eq!(spec.timeout_secs, 60);
    }

    #[test]
    fn parse_notify_cfg_native() {
        let cfg = parse_notify_cfg(Some("native"));
        assert!(cfg.native);
        assert!(cfg.imessage_target.is_none());
    }

    #[test]
    fn parse_notify_cfg_full() {
        let cfg = parse_notify_cfg(Some(
            "native,imessage:koosha@icloud.com,email:k@k.com,webhook:https://ntfy.sh/x",
        ));
        assert!(cfg.native);
        assert_eq!(cfg.imessage_target.as_deref(), Some("koosha@icloud.com"));
        assert_eq!(cfg.email_target.as_deref(), Some("k@k.com"));
        assert_eq!(
            cfg.webhook_url.as_deref(),
            Some("https://ntfy.sh/x")
        );
    }

    #[test]
    fn parse_notify_cfg_empty() {
        let cfg = parse_notify_cfg(None);
        assert!(!cfg.native);
    }
}
