// DAST configuration and report parsing.
//
// A repo opts into DAST by shipping `.qgate/dast.toml` with `base_url` and
// (optionally) `schema_url` pointing at an OpenAPI document. Falling back to
// `QGATE_DAST_BASE_URL` / `QGATE_DAST_SCHEMA_URL` env vars makes it easy to
// drive from CI without committing internal URLs.

use std::path::Path;

#[derive(Debug, Clone)]
pub(crate) struct DastConfig {
    pub base_url: String,
    pub schema_url: Option<String>,
}

impl DastConfig {
    pub fn discover(root: &Path) -> Option<Self> {
        // 1) .qgate/dast.toml
        let toml_path = root.join(".qgate/dast.toml");
        if toml_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&toml_path) {
                if let Ok(v) = toml::from_str::<toml::Value>(&content) {
                    let base_url = v.get("base_url")?.as_str()?.to_string();
                    let schema_url = v
                        .get("schema_url")
                        .and_then(|s| s.as_str())
                        .map(String::from);
                    if !base_url.is_empty() {
                        return Some(Self {
                            base_url,
                            schema_url,
                        });
                    }
                }
            }
        }
        // 2) Environment variables
        let base_url = std::env::var("QGATE_DAST_BASE_URL").ok()?;
        if base_url.is_empty() {
            return None;
        }
        let schema_url = std::env::var("QGATE_DAST_SCHEMA_URL")
            .ok()
            .filter(|s| !s.is_empty());
        Some(Self {
            base_url,
            schema_url,
        })
    }
}

/// Parse the high/critical finding count out of a semgrep JSON report.
/// Returns 0.0 if the file is missing, unreadable, or has no findings array.
pub(crate) fn parse_semgrep_high_count(path: &str) -> f64 {
    let Ok(content) = std::fs::read_to_string(path) else {
        return 0.0;
    };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&content) else {
        return 0.0;
    };
    let results = v
        .get("results")
        .and_then(|r| r.as_array())
        .cloned()
        .unwrap_or_default();
    let mut count: f64 = 0.0;
    for finding in results {
        let severity = finding
            .get("extra")
            .and_then(|e| e.get("severity"))
            .and_then(|s| s.as_str())
            .unwrap_or("");
        if severity.eq_ignore_ascii_case("error")
            || severity.eq_ignore_ascii_case("warning")
            || severity.eq_ignore_ascii_case("high")
            || severity.eq_ignore_ascii_case("critical")
        {
            count += 1.0;
        }
    }
    count
}

/// Parse the failed-check count out of a schemathesis JSON report.
/// Returns 0.0 if missing/unreadable; counts `failed_examples` if present
/// and `checks[].status == "failure"` markers as a fallback.
pub(crate) fn parse_dast_failed_count(path: &std::path::Path) -> f64 {
    let Ok(content) = std::fs::read_to_string(path) else {
        return 0.0;
    };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&content) else {
        return 0.0;
    };
    if let Some(n) = v.get("failed_examples").and_then(|n| n.as_f64()) {
        return n;
    }
    if let Some(n) = v
        .get("summary")
        .and_then(|s| s.get("failed"))
        .and_then(|n| n.as_f64())
    {
        return n;
    }
    if let Some(arr) = v.get("checks").and_then(|c| c.as_array()) {
        let fails = arr
            .iter()
            .filter(|c| c.get("status").and_then(|s| s.as_str()) == Some("failure"))
            .count();
        return fails as f64;
    }
    0.0
}
