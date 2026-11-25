//! `sl` CLI client — talks to a running `sl-daemon` HTTP server.
//!
//! ## Exit codes (daemon client subcommands)
//!
//! * `0` — success
//! * `1` — daemon not running, validation failed, or empty search results
//! * `2` — usage / I/O / network / parse error

use reqwest::Client;

use crate::resilience::{reqwest_error_is_retryable, RetryPolicy};

/// Successful command completion.
pub const EXIT_OK: i32 = 0;
/// Daemon unreachable, validation failed, or empty search results.
pub const EXIT_NOT_OK: i32 = 1;
/// Unexpected error (I/O, parse, non-connect HTTP failure).
pub const EXIT_ERROR: i32 = 2;

/// Default base URL of the daemon HTTP server.
pub const DEFAULT_BASE_URL: &str = "http://127.0.0.1:8080";

/// Hint printed when the daemon HTTP listener is not reachable.
pub fn daemon_down_message(base_url: &str) -> String {
    format!(
        "daemon not running at {base_url} — start with: \
         sl-daemon serve --out <okf-out-dir> (auto-discovers local session roots)"
    )
}

pub fn eprint_daemon_down(base_url: &str) {
    eprintln!("{}", daemon_down_message(base_url));
}

pub fn eprint_error(message: impl std::fmt::Display) {
    eprintln!("error: {message}");
}

pub fn exit_daemon_down(base_url: &str) -> ! {
    eprint_daemon_down(base_url);
    std::process::exit(EXIT_NOT_OK);
}

pub fn exit_error(message: impl std::fmt::Display) -> ! {
    eprint_error(message);
    std::process::exit(EXIT_ERROR);
}

/// Map a `reqwest` failure from a daemon HTTP call to a process exit.
pub fn exit_on_reqwest(base_url: &str, context: &str, err: reqwest::Error) -> ! {
    if err.is_connect() {
        exit_daemon_down(base_url);
    }
    exit_error(format!("{context}: {err}"));
}

/// Build a full URL from a base URL and a path segment.
///
/// Trailing slashes on `base` are stripped so that `build_url("http://host/", "/path")`
/// produces `"http://host/path"` rather than `"http://host//path"`.
pub fn build_url(base: &str, path: &str) -> String {
    let base = base.trim_end_matches('/');
    format!("{base}{path}")
}

/// Outcome of a `/healthz` probe.
#[derive(Debug, PartialEq, Eq)]
pub enum HealthStatus {
    /// Daemon is reachable and responded.
    Running { body: String },
    /// Connection refused — daemon not running.
    NotRunning,
}

/// Fetch daemon health status.
///
/// Returns `Ok(HealthStatus::Running)` when the daemon is reachable.
/// Returns `Ok(HealthStatus::NotRunning)` when the connection is refused.
/// Returns `Err` for other network / parse failures.
///
/// Transient connect/timeout/request failures are retried per [`RetryPolicy`]
/// (`SL_HTTP_RETRY_MAX` / `SL_HTTP_RETRY_BASE_MS`).
pub async fn fetch_health(client: &Client, base_url: &str) -> Result<HealthStatus, reqwest::Error> {
    let policy = RetryPolicy::from_env().unwrap_or_else(|_| RetryPolicy::default_policy());
    policy
        .run(
            |_| async {
                let url = build_url(base_url, "/healthz");
                let resp = match client.get(&url).send().await {
                    Ok(r) => r,
                    Err(e) if e.is_connect() => return Ok(HealthStatus::NotRunning),
                    Err(e) => return Err(e),
                };
                let body = resp.text().await?;
                Ok(HealthStatus::Running { body })
            },
            |err| reqwest_error_is_retryable(err) && !err.is_connect(),
        )
        .await
}

/// Fetch bundle list from the daemon.
///
/// The daemon's `/api/bundles` returns a JSON array of parsed OKF documents;
/// we extract just the file path from the `"path"` field of each object when
/// present, falling back to a serialized representation otherwise.
///
/// Transient connect/timeout/request failures are retried per [`RetryPolicy`].
pub async fn fetch_bundle_paths(
    client: &Client,
    base_url: &str,
) -> Result<Vec<String>, reqwest::Error> {
    let policy = RetryPolicy::from_env().unwrap_or_else(|_| RetryPolicy::default_policy());
    policy
        .run(
            |_| async {
                let url = build_url(base_url, "/api/bundles");
                let resp = client.get(&url).send().await?;
                let values: Vec<serde_json::Value> = resp.json().await?;
                let paths = values
                    .into_iter()
                    .map(|v| {
                        v.get("path")
                            .and_then(|p| p.as_str())
                            .map(|s| s.to_owned())
                            .unwrap_or_else(|| v.to_string())
                    })
                    .collect();
                Ok(paths)
            },
            reqwest_error_is_retryable,
        )
        .await
}

// ---------------------------------------------------------------------------
// Unit tests (no network required)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn build_url_appends_path() {
        assert_eq!(build_url("http://localhost:9001", "/healthz"), "http://localhost:9001/healthz");
    }

    #[test]
    fn build_url_strips_trailing_slash_from_base() {
        assert_eq!(
            build_url("http://localhost:9001/", "/api/bundles"),
            "http://localhost:9001/api/bundles"
        );
    }

    #[test]
    fn build_url_works_with_no_leading_slash_on_path() {
        assert_eq!(
            build_url("http://localhost:9001", "/api/stream"),
            "http://localhost:9001/api/stream"
        );
    }

    #[test]
    fn daemon_down_message_includes_start_hint() {
        let msg = daemon_down_message("http://127.0.0.1:8080");
        assert!(msg.contains("daemon not running"));
        assert!(msg.contains("sl-daemon serve"));
    }

    #[test]
    fn fetch_bundle_paths_extracts_path_field() {
        let json = r#"[{"path":"/out/a.okf.json","title":"A"},{"path":"/out/b.okf.json"}]"#;
        let values: Vec<serde_json::Value> = serde_json::from_str(json).unwrap();
        let paths: Vec<String> = values
            .into_iter()
            .map(|v| {
                v.get("path")
                    .and_then(|p| p.as_str())
                    .map(|s| s.to_owned())
                    .unwrap_or_else(|| v.to_string())
            })
            .collect();
        assert_eq!(paths, vec!["/out/a.okf.json", "/out/b.okf.json"]);
    }
}
