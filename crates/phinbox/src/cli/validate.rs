//! `phinbox validate` subcommand implementation.
//!
//! Validates a JSON `PromptSpec` *without* rendering it. This is the CI
//! entry point: it must never open a popup and must never touch the inbox.
//!
//! The checks deliberately reuse the render path's own gate
//! ([`phinbox::spec::PromptSpec::validate`], called by
//! `phinbox::render::dispatch`) plus an idempotent serde round-trip, so a
//! spec that passes `validate` cannot be rejected by `ask` for a reason
//! that lives on this side of the boundary.

use std::path::PathBuf;

use phinbox::spec::PromptSpec;
use serde_json::{json, Value};

/// Validate a JSON spec without rendering it.
///
/// Prints a machine-readable envelope and exits 0 when the spec is valid;
/// prints the same envelope with `"valid": false` and exits non-zero when
/// it is not.
#[derive(Debug, clap::Args)]
#[command(group = clap::ArgGroup::new("source").required(true).args(["from_file", "from_json"]))]
pub struct ValidateArgs {
    /// Validate the JSON spec in this file.
    #[arg(long, value_name = "PATH")]
    pub from_file: Option<PathBuf>,

    /// Validate an inline JSON spec.
    #[arg(long, value_name = "JSON")]
    pub from_json: Option<String>,
}

/// Where a spec came from, for the report envelope.
fn read_source(args: &ValidateArgs) -> Result<(String, String), String> {
    if let Some(path) = &args.from_file {
        let text =
            std::fs::read_to_string(path).map_err(|e| format!("read {}: {e}", path.display()))?;
        return Ok((path.display().to_string(), text));
    }
    let inline = args
        .from_json
        .clone()
        .ok_or_else(|| "provide --from-file <PATH> or --from-json <JSON>".to_string())?;
    Ok(("--from-json".to_string(), inline))
}

/// Parse, validate, and round-trip a spec. Returns the success envelope.
///
/// Public so the CLI tests can exercise it without spawning a process.
pub fn check_spec(raw: &str, source: &str) -> Result<Value, String> {
    let spec: PromptSpec = serde_json::from_str(raw).map_err(|e| format!("parse {source}: {e}"))?;

    // Same gate the render path applies (`render::dispatch`).
    spec.validate()?;

    // Serde round-trip: the spec must survive encode → decode → encode
    // unchanged. Catches asymmetric `Serialize`/`Deserialize` impls that
    // would let `ask --from-json` and `ask --from-file` disagree.
    let first = serde_json::to_value(&spec).map_err(|e| format!("serialize {source}: {e}"))?;
    let reparsed: PromptSpec = serde_json::from_value(first.clone())
        .map_err(|e| format!("serde round-trip failed for {source}: {e}"))?;
    let second = serde_json::to_value(&reparsed).map_err(|e| format!("serialize {source}: {e}"))?;
    if first != second {
        return Err(format!("serde round-trip is not stable for {source}"));
    }

    let field_kind = first
        .get("field")
        .and_then(|f| f.get("kind"))
        .and_then(Value::as_str)
        .unwrap_or("unknown");

    let mut envelope = json!({
        "valid": true,
        "source": source,
        "title": spec.title,
        "field_kind": field_kind,
        "urgency": first.get("urgency").cloned().unwrap_or(json!("info")),
        "timeout_secs": spec.timeout_secs,
    });
    if let Some(id) = &spec.request_id {
        envelope["request_id"] = json!(id);
    }
    Ok(envelope)
}

pub fn cmd_validate(args: ValidateArgs) -> Result<(), String> {
    let (source, raw) = read_source(&args)?;
    match check_spec(&raw, &source) {
        Ok(envelope) => {
            println!("{}", serde_json::to_string_pretty(&envelope).unwrap());
            Ok(())
        },
        Err(err) => {
            let envelope = json!({ "valid": false, "source": source, "error": err });
            println!("{}", serde_json::to_string_pretty(&envelope).unwrap());
            Err(err)
        },
    }
}

#[cfg(test)]
mod tests {
    use clap::Parser;

    use super::*;

    const VALID: &str = r#"{"title":"Deploy?","question":"Ship it?",
        "field":{"kind":"boolean","label":"Confirm","default":true}}"#;

    fn args(from_json: Option<&str>, from_file: Option<PathBuf>) -> ValidateArgs {
        ValidateArgs {
            from_json: from_json.map(str::to_string),
            from_file,
        }
    }

    #[test]
    fn check_spec_accepts_minimal_boolean() {
        let env = check_spec(VALID, "--from-json").unwrap();
        assert_eq!(env["valid"], json!(true));
        assert_eq!(env["field_kind"], json!("boolean"));
        assert_eq!(env["title"], json!("Deploy?"));
        assert_eq!(env["timeout_secs"], json!(600));
    }

    #[test]
    fn check_spec_rejects_empty_title() {
        let raw = VALID.replace("Deploy?", "");
        let err = check_spec(&raw, "--from-json").unwrap_err();
        assert_eq!(err, "title must not be empty");
    }

    #[test]
    fn check_spec_rejects_unknown_field_kind() {
        let raw = r#"{"title":"t","question":"q","field":{"kind":"nope","label":"l"}}"#;
        let err = check_spec(raw, "--from-json").unwrap_err();
        assert!(err.starts_with("parse --from-json:"), "got {err}");
    }

    #[test]
    fn check_spec_rejects_unknown_toplevel_key() {
        // `PromptSpec` is `deny_unknown_fields`; a typo must not validate.
        let raw = r#"{"title":"t","question":"q","fieldd":{"kind":"text","label":"l"}}"#;
        assert!(check_spec(raw, "--from-json").is_err());
    }

    #[test]
    fn check_spec_rejects_bad_choice_default_index() {
        let raw = r#"{"title":"t","question":"q","field":{"kind":"choice","label":"l",
            "options":[{"value":"a","label":"A"}],"default_index":3}}"#;
        let err = check_spec(raw, "--from-json").unwrap_err();
        assert!(err.contains("out of range"), "got {err}");
    }

    #[test]
    fn check_spec_is_stable_for_choice_fields() {
        let raw = r#"{"title":"t","question":"q","field":{"kind":"choice","label":"l",
            "options":[{"value":"a","label":"A"}],"default_index":0}}"#;
        let env = check_spec(raw, "--from-json").unwrap();
        assert_eq!(env["field_kind"], json!("choice"));
    }

    #[test]
    fn read_source_reads_a_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("spec.json");
        std::fs::write(&path, VALID).unwrap();
        let (source, raw) = read_source(&args(None, Some(path.clone()))).unwrap();
        assert_eq!(source, path.display().to_string());
        assert_eq!(raw, VALID);
    }

    #[test]
    fn read_source_reports_a_missing_file() {
        let err =
            read_source(&args(None, Some(PathBuf::from("/nonexistent/spec.json")))).unwrap_err();
        assert!(err.starts_with("read /nonexistent/spec.json:"), "got {err}");
    }

    #[test]
    fn parses_from_file_and_from_json() {
        #[derive(Parser)]
        struct Wrapper {
            #[command(subcommand)]
            cmd: TestCmd,
        }
        #[derive(clap::Subcommand)]
        enum TestCmd {
            Validate(ValidateArgs),
        }

        let cli = Wrapper::try_parse_from(["t", "validate", "--from-file", "spec.json"]).unwrap();
        let TestCmd::Validate(a) = cli.cmd;
        assert_eq!(
            a.from_file.as_deref(),
            Some(std::path::Path::new("spec.json"))
        );
        assert!(a.from_json.is_none());

        let cli = Wrapper::try_parse_from(["t", "validate", "--from-json", VALID]).unwrap();
        let TestCmd::Validate(a) = cli.cmd;
        assert!(a.from_json.is_some());

        // `--from-file` and `--from-json` are mutually exclusive.
        assert!(Wrapper::try_parse_from([
            "t",
            "validate",
            "--from-file",
            "spec.json",
            "--from-json",
            "{}"
        ])
        .is_err());
    }
}
