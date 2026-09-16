//! `phinbox answer` subcommand implementation.

use std::path::PathBuf;

use phinbox::inbox::{finalize, RequestState};
use phinbox::spec::{ElicitResponse, FieldSpec, FieldValue};
use serde_json::json;

/// Submit an answer to a queued inbox request via the CLI (no UI).
#[derive(Debug, clap::Args)]
pub struct AnswerArgs {
    /// The request ID to answer.
    #[arg(long)]
    pub request_id: String,
    /// Text value (for text, long-text, choice, or date-time fields).
    #[arg(long)]
    pub value: Option<String>,
    /// Integer value.
    #[arg(long)]
    pub integer: Option<i64>,
    /// Boolean value.
    #[arg(long)]
    pub boolean: Option<bool>,
    /// Cancel instead of answering.
    #[arg(long)]
    pub cancel: bool,
    /// Optional notes.
    #[arg(long)]
    pub notes: Option<String>,
}

pub fn cmd_answer(args: AnswerArgs, inbox_dir: &PathBuf) -> Result<(), String> {
    let mut req = phinbox::inbox::load(inbox_dir, &args.request_id)
        .map_err(|e| e.to_string())?;

    if req.is_terminal() {
        return Err(format!(
            "request {} is already in terminal state {:?}",
            req.request_id, req.state
        ));
    }

    let response = if args.cancel {
        ElicitResponse::Cancelled {
            notes: args.notes.clone(),
        }
    } else if let Some(n) = args.integer {
        ElicitResponse::Answered {
            value: FieldValue::Integer(n),
            notes: args.notes.clone(),
        }
    } else if let Some(b) = args.boolean {
        ElicitResponse::Answered {
            value: FieldValue::Boolean(b),
            notes: args.notes.clone(),
        }
    } else if let Some(v) = args.value {
        let value = match &req.spec.field {
            FieldSpec::Text { .. } => FieldValue::Text(v),
            FieldSpec::LongText { .. } => FieldValue::LongText(v),
            FieldSpec::Choice { options, .. } => {
                let idx = options
                    .iter()
                    .position(|o| o.value == v || o.label == v)
                    .ok_or_else(|| format!("choice '{v}' not in options"))?;
                FieldValue::Choice {
                    value: options[idx].value.clone(),
                    index: idx,
                }
            }
            FieldSpec::DateTime { .. } => FieldValue::DateTime(v),
            _ => return Err("use --integer or --boolean for this field type".into()),
        };
        ElicitResponse::Answered {
            value,
            notes: args.notes.clone(),
        }
    } else {
        return Err("one of --value / --integer / --boolean / --cancel is required".into());
    };

    req.state = match response {
        ElicitResponse::Cancelled { .. } => RequestState::Cancelled,
        _ => RequestState::Answered,
    };
    req.response = Some(response.clone());

    finalize(inbox_dir, &req).map_err(|e| e.to_string())?;
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "status": "submitted",
            "request_id": req.request_id,
            "response": response,
        }))
        .map_err(|e| e.to_string())?
    );
    Ok(())
}
