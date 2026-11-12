//! Implementations of the `byteport` headless subcommands.
//!
//! These are the subcommands that run without a display server and emit JSON on
//! stdout: `version` reports the build identity, and `transport status` /
//! `transport check` report and probe the S3-compatible upload transport.
//!
//! Every entry point returns [`CliError`], which `main.rs` maps to a stderr
//! diagnostic plus a non-zero exit code.

use std::io::Write;

use byteport_transport::{S3UploadTransport, UploadRequest, UploadTransport};
use serde_json::json;

use crate::CliError;

/// Environment variable holding the S3-compatible upload endpoint.
const ENV_UPLOAD_URL: &str = "BYTEPORT_UPLOAD_URL";

/// Environment variable holding the target upload bucket.
const ENV_UPLOAD_BUCKET: &str = "BYTEPORT_UPLOAD_BUCKET";

/// Dev default endpoint, mirroring the desktop wiring in `lib.rs`.
const DEFAULT_UPLOAD_URL: &str = "https://uploads.byteport.local";

/// Dev default bucket, mirroring the desktop wiring in `lib.rs`.
const DEFAULT_UPLOAD_BUCKET: &str = "byteport-uploads";

/// Key prefix applied by the desktop shell, reused here so `transport
/// check` exercises the same wiring the GUI uses.
const UPLOAD_KEY_PREFIX: &str = "desktop";

/// Synthetic object key used by `transport check` to prove the transport
/// can mint an upload instruction.
const PROBE_OBJECT_KEY: &str = "_healthcheck/transport-check";

/// Content type sent with the synthetic probe upload.
const PROBE_CONTENT_TYPE: &str = "application/json";

/// Content length sent with the synthetic probe upload.
const PROBE_CONTENT_LENGTH: u64 = 2;

/// Upload transport configuration resolved from the environment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct UploadConfig {
    /// Effective endpoint URL.
    url: String,
    /// Effective bucket name.
    bucket: String,
    /// Whether `url` came from the environment rather than the default.
    url_from_env: bool,
    /// Whether `bucket` came from the environment rather than the default.
    bucket_from_env: bool,
}

/// Environment lookup used by the real binary; tests inject their own.
pub(crate) fn default_env_lookup() -> impl Fn(&str) -> Option<String> {
    |key| std::env::var(key).ok()
}

/// Resolve the effective upload configuration.
///
/// A variable that is unset *or* blank falls back to the dev default, so
/// `url_from_env`/`bucket_from_env` mean "the effective value came from
/// the environment".
pub(crate) fn resolve_upload_config(lookup: &dyn Fn(&str) -> Option<String>) -> UploadConfig {
    let env_url = lookup(ENV_UPLOAD_URL).filter(|value| !value.trim().is_empty());
    let env_bucket = lookup(ENV_UPLOAD_BUCKET).filter(|value| !value.trim().is_empty());

    UploadConfig {
        url_from_env: env_url.is_some(),
        bucket_from_env: env_bucket.is_some(),
        url: env_url.unwrap_or_else(|| DEFAULT_UPLOAD_URL.to_string()),
        bucket: env_bucket.unwrap_or_else(|| DEFAULT_UPLOAD_BUCKET.to_string()),
    }
}

/// `byteport version` — name, crate version, and git revision as JSON.
pub(crate) fn cmd_version(out: &mut dyn Write) -> Result<(), CliError> {
    let payload = json!({
        "name": "byteport",
        "version": env!("CARGO_PKG_VERSION"),
        "build_id": build_id(),
    });

    write_json(out, &payload)
}

/// `byteport transport status` — resolved endpoint/bucket plus provenance.
pub(crate) fn cmd_transport_status(config: &UploadConfig, out: &mut dyn Write) -> Result<(), CliError> {
    let payload = json!({
        "url": config.url,
        "bucket": config.bucket,
        "configured_via_env": {
            "url": config.url_from_env,
            "bucket": config.bucket_from_env,
        },
    });

    write_json(out, &payload)
}

/// `byteport transport check` — mint a probe upload instruction and
/// assert the transport resolved it as expected.
///
/// Fails (non-zero exit) when the endpoint or bucket is unusable, when
/// the transport rejects the probe, or when the returned instruction
/// disagrees with the configured endpoint/bucket/key prefix.
pub(crate) fn cmd_transport_check(config: &UploadConfig, out: &mut dyn Write) -> Result<(), CliError> {
    validate_endpoint(&config.url)?;

    if config.bucket.trim().is_empty() {
        return Err(CliError::Config("upload bucket is empty".to_string()));
    }

    let transport = S3UploadTransport::new(config.url.as_str(), config.bucket.as_str(), Some(UPLOAD_KEY_PREFIX));

    let instruction = transport.create_upload(&UploadRequest {
        object_key: PROBE_OBJECT_KEY.to_string(),
        content_type: PROBE_CONTENT_TYPE.to_string(),
        content_length: PROBE_CONTENT_LENGTH,
    })?;

    let expected_key = format!("{UPLOAD_KEY_PREFIX}/{}", PROBE_OBJECT_KEY.trim_start_matches('/'));
    let resolved_key = object_key_from_url(&instruction.url, &config.url, &config.bucket).ok_or_else(|| {
        CliError::Config(format!(
            "transport returned an upload URL outside {}/{}/: {}",
            config.url.trim_end_matches('/'),
            config.bucket,
            instruction.url
        ))
    })?;

    if resolved_key != expected_key {
        return Err(CliError::Config(format!(
            "transport resolved object key {resolved_key:?}, expected {expected_key:?}"
        )));
    }

    if instruction.method != "PUT" {
        return Err(CliError::Config(format!(
            "transport returned method {:?}, expected \"PUT\"",
            instruction.method
        )));
    }

    // The transport exposes no server-side session id; the object key is
    // this upload's stable identity, so it is reported as `upload_id` and
    // tagged with `upload_id_kind` to keep the semantics unambiguous.
    let payload = json!({
        "ok": true,
        "upload_id": resolved_key,
        "upload_id_kind": "object_key",
        "endpoint": config.url,
        "bucket": config.bucket,
        "method": instruction.method,
        "target_url": instruction.url,
        "headers": instruction.headers,
    });

    write_json(out, &payload)
}

/// Serialize `value` as pretty JSON followed by a newline.
fn write_json(out: &mut dyn Write, value: &serde_json::Value) -> Result<(), CliError> {
    serde_json::to_writer_pretty(&mut *out, value)?;
    out.write_all(b"\n")?;
    Ok(())
}

/// Reject endpoints the S3 transport cannot build a URL from.
fn validate_endpoint(endpoint: &str) -> Result<(), CliError> {
    let trimmed = endpoint.trim();

    if trimmed.is_empty() {
        return Err(CliError::Config("upload endpoint is empty".to_string()));
    }

    if !(trimmed.starts_with("http://") || trimmed.starts_with("https://")) {
        return Err(CliError::Config(format!(
            "upload endpoint must be an http(s) URL, got {trimmed:?}"
        )));
    }

    Ok(())
}

/// Extract the object key from a transport-built upload URL, or `None`
/// when the URL does not sit under `endpoint/bucket/`.
fn object_key_from_url(url: &str, endpoint: &str, bucket: &str) -> Option<String> {
    let prefix = format!("{}/{}/", endpoint.trim_end_matches('/'), bucket);
    url.strip_prefix(&prefix).map(str::to_string)
}

/// Short git revision of the working tree, or `dev` when unavailable.
fn build_id() -> String {
    git_short_revision().unwrap_or_else(|| "dev".to_string())
}

/// Run `git rev-parse --short HEAD`, returning `None` on any failure so
/// the CLI still works from a release tarball without a `.git` directory.
fn git_short_revision() -> Option<String> {
    let output = std::process::Command::new("git")
        .arg("rev-parse")
        .arg("--short")
        .arg("HEAD")
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let revision = String::from_utf8(output.stdout).ok()?;
    let revision = revision.trim();

    if revision.is_empty() {
        None
    } else {
        Some(revision.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn env_with(url: Option<&str>, bucket: Option<&str>) -> impl Fn(&str) -> Option<String> {
        let url = url.map(str::to_string);
        let bucket = bucket.map(str::to_string);
        move |key: &str| match key {
            ENV_UPLOAD_URL => url.clone(),
            ENV_UPLOAD_BUCKET => bucket.clone(),
            _ => None,
        }
    }

    fn render_check(config: &UploadConfig) -> serde_json::Value {
        let mut buffer = Vec::new();
        cmd_transport_check(config, &mut buffer).expect("transport check should succeed");
        serde_json::from_slice(&buffer).expect("check output should be valid json")
    }

    // ---- version -------------------------------------------------------

    #[test]
    fn version_output_is_json_with_name_version_and_build_id() {
        let mut buffer = Vec::new();
        cmd_version(&mut buffer).expect("version should render");

        let value: serde_json::Value = serde_json::from_slice(&buffer).expect("version output should be valid json");

        assert_eq!(value["name"], serde_json::json!("byteport"));
        assert_eq!(value["version"], serde_json::json!(env!("CARGO_PKG_VERSION")));
        assert!(
            value["build_id"].as_str().map(|id| !id.is_empty()).unwrap_or(false),
            "build_id should be a non-empty string, got {value:?}"
        );
    }

    // ---- config resolution ---------------------------------------------

    #[test]
    fn config_falls_back_to_dev_defaults() {
        let config = resolve_upload_config(&env_with(None, None));

        assert_eq!(config.url, DEFAULT_UPLOAD_URL);
        assert_eq!(config.bucket, DEFAULT_UPLOAD_BUCKET);
        assert!(!config.url_from_env);
        assert!(!config.bucket_from_env);
    }

    #[test]
    fn blank_env_values_are_treated_as_unset() {
        let config = resolve_upload_config(&env_with(Some("   "), Some("")));

        assert_eq!(config.url, DEFAULT_UPLOAD_URL);
        assert_eq!(config.bucket, DEFAULT_UPLOAD_BUCKET);
        assert!(!config.url_from_env);
        assert!(!config.bucket_from_env);
    }

    #[test]
    fn env_values_win_and_are_reported_as_env_sourced() {
        let config = resolve_upload_config(&env_with(
            Some("https://uploads.example.test"),
            Some("byteport-ci-uploads"),
        ));

        assert_eq!(config.url, "https://uploads.example.test");
        assert_eq!(config.bucket, "byteport-ci-uploads");
        assert!(config.url_from_env);
        assert!(config.bucket_from_env);
    }

    // ---- transport status ----------------------------------------------

    #[test]
    fn status_reports_defaults_and_partial_env_provenance() {
        let mut buffer = Vec::new();
        let config = resolve_upload_config(&env_with(Some("https://uploads.example.test"), None));
        cmd_transport_status(&config, &mut buffer).expect("status should render");

        let value: serde_json::Value = serde_json::from_slice(&buffer).expect("status output should be valid json");

        assert_eq!(value["url"], serde_json::json!("https://uploads.example.test"));
        assert_eq!(value["bucket"], serde_json::json!(DEFAULT_UPLOAD_BUCKET));
        assert_eq!(value["configured_via_env"]["url"], serde_json::json!(true));
        assert_eq!(value["configured_via_env"]["bucket"], serde_json::json!(false));
    }

    // ---- transport check ------------------------------------------------

    #[test]
    fn check_succeeds_and_reports_resolved_upload() {
        let config = resolve_upload_config(&env_with(
            Some("https://uploads.example.test"),
            Some("byteport-uploads"),
        ));

        let value = render_check(&config);

        let expected_key = format!("{UPLOAD_KEY_PREFIX}/{PROBE_OBJECT_KEY}");

        assert_eq!(value["ok"], serde_json::json!(true));
        assert_eq!(value["upload_id"], serde_json::json!(expected_key.clone()));
        assert_eq!(value["upload_id_kind"], serde_json::json!("object_key"));
        assert_eq!(value["endpoint"], serde_json::json!("https://uploads.example.test"));
        assert_eq!(value["bucket"], serde_json::json!("byteport-uploads"));
        assert_eq!(value["method"], serde_json::json!("PUT"));
        assert_eq!(
            value["target_url"],
            serde_json::json!(format!("https://uploads.example.test/byteport-uploads/{expected_key}"))
        );
        assert_eq!(value["headers"]["content-type"], serde_json::json!(PROBE_CONTENT_TYPE));
        assert_eq!(
            value["headers"]["content-length"],
            serde_json::json!(PROBE_CONTENT_LENGTH.to_string())
        );
    }

    #[test]
    fn check_succeeds_on_default_configuration() {
        let config = resolve_upload_config(&env_with(None, None));
        let value = render_check(&config);

        assert_eq!(value["ok"], serde_json::json!(true));
        assert_eq!(value["endpoint"], serde_json::json!(DEFAULT_UPLOAD_URL));
    }

    #[test]
    fn check_rejects_non_http_endpoint() {
        let config = UploadConfig {
            url: "ftp://uploads.example.test".to_string(),
            bucket: "byteport-uploads".to_string(),
            url_from_env: true,
            bucket_from_env: false,
        };

        let error = cmd_transport_check(&config, &mut Vec::new()).expect_err("non-http endpoint should fail");

        assert!(
            matches!(error, CliError::Config(_)),
            "expected a config error, got {error:?}"
        );
    }

    #[test]
    fn check_rejects_empty_endpoint_and_bucket() {
        let empty_url = UploadConfig {
            url: String::new(),
            bucket: "byteport-uploads".to_string(),
            url_from_env: true,
            bucket_from_env: false,
        };
        assert!(cmd_transport_check(&empty_url, &mut Vec::new()).is_err());

        let empty_bucket = UploadConfig {
            url: "https://uploads.example.test".to_string(),
            bucket: "  ".to_string(),
            url_from_env: false,
            bucket_from_env: true,
        };
        assert!(cmd_transport_check(&empty_bucket, &mut Vec::new()).is_err());
    }

    // ---- helpers --------------------------------------------------------

    #[test]
    fn object_key_from_url_strips_endpoint_and_bucket() {
        let key = object_key_from_url(
            "https://uploads.example.test/byteport-uploads/desktop/demo.png",
            "https://uploads.example.test/",
            "byteport-uploads",
        );
        assert_eq!(key.as_deref(), Some("desktop/demo.png"));
    }

    #[test]
    fn object_key_from_url_rejects_foreign_urls() {
        assert_eq!(
            object_key_from_url(
                "https://other.example.test/byteport-uploads/desktop/demo.png",
                "https://uploads.example.test",
                "byteport-uploads",
            ),
            None
        );
    }
}
