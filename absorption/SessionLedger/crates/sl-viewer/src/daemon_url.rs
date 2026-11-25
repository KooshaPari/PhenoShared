//! Shared `sl-daemon` HTTP base URL for viewer API calls.
//!
//! Override at compile time with `SL_DAEMON_URL` (see `.env.example`).

/// Default daemon base URL when `SL_DAEMON_URL` is not set at compile time.
pub const DEFAULT_DAEMON_BASE: &str = "http://127.0.0.1:8080";

/// Resolved daemon base URL (no trailing slash).
///
/// Reads `SL_DAEMON_URL` from the compile-time environment when set.
pub fn daemon_base_url() -> &'static str {
    option_env!("SL_DAEMON_URL").unwrap_or(DEFAULT_DAEMON_BASE)
}

/// Build a full URL for a daemon API path (e.g. `/api/search` or `/api/stream`).
pub fn daemon_api_url(path: &str) -> String {
    let base = daemon_base_url().trim_end_matches('/');
    let path = path.trim_start_matches('/');
    format!("{base}/{path}")
}

/// Human-readable host display for error messages (scheme stripped).
pub fn daemon_host_display() -> String {
    daemon_base_url()
        .trim_start_matches("http://")
        .trim_start_matches("https://")
        .trim_end_matches('/')
        .to_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_daemon_base_is_localhost_8080() {
        assert_eq!(DEFAULT_DAEMON_BASE, "http://127.0.0.1:8080");
    }

    #[test]
    fn daemon_api_url_joins_base_and_path() {
        let url = daemon_api_url("/api/stream");
        assert!(url.ends_with("/api/stream"), "got {url}");
        assert!(url.starts_with("http://"), "got {url}");
    }

    #[test]
    fn daemon_api_url_accepts_path_without_leading_slash() {
        let url = daemon_api_url("api/search");
        assert!(url.ends_with("/api/search"), "got {url}");
    }

    #[test]
    fn daemon_host_display_strips_scheme() {
        let display = daemon_host_display();
        assert!(!display.starts_with("http"), "got {display}");
        assert!(display.contains("8080"), "got {display}");
    }
}
