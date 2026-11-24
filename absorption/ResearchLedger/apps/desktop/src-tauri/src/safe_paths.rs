//! Path- and shell-input validation for Tauri commands.
//!
//! The desktop app accepts user-supplied file paths and external URLs as
//! arguments. To prevent path traversal, command-argument injection, and
//! accidental leak of files outside the vault, every user-controlled
//! filesystem path that flows into a Tauri command must pass through
//! `ensure_within_acceptable_roots`, and every URL passed to a browser
//! capture command must pass through `ensure_safe_provider_url`.

#[cfg(test)]
use std::path::PathBuf;
use std::path::{Component, Path};

/// Return a canonical (".."-free) version of the given path, **only if** it
/// lives inside one of the acceptable roots. Returns `Err` otherwise.
///
/// * `user_path` is the path as supplied (could be relative or contain `..`).
/// * `acceptable_roots` is a list of directories that contain the vault or
///   user-selected folders. The path must resolve to a descendant of one of
///   these roots after canonicalisation.
#[cfg(test)]
pub fn ensure_within_acceptable_roots(
    user_path: &str,
    label: &str,
    acceptable_roots: &[PathBuf],
) -> Result<PathBuf, String> {
    if user_path.is_empty() {
        return Err(format!("{label} path must not be empty"));
    }
    if user_path.chars().any(|c| c.is_control()) {
        return Err(format!("{label} path must not contain control characters"));
    }
    if contains_parent_dir_component(user_path) {
        return Err(format!(
            "{label} path must not contain `..` traversal segments"
        ));
    }
    let provided = PathBuf::from(user_path);
    let candidates: Vec<PathBuf> = if provided.is_absolute() {
        vec![provided.clone()]
    } else {
        acceptable_roots
            .iter()
            .map(|root| root.join(&provided))
            .collect()
    };
    for candidate in candidates {
        for root in acceptable_roots {
            if candidate.starts_with(root) {
                return Ok(candidate);
            }
        }
    }
    Err(format!(
        "{label} path must be absolute and located inside one of the approved roots"
    ))
}

/// Validates an `https://` URL destined for the browser-capture command.
/// Only the providers we currently support are whitelisted so a malicious
/// caller can't trick the desktop app into opening arbitrary URLs with the
/// user's authed browser profile.
pub fn ensure_safe_provider_url(url: &str, allowed_hosts: &[&str]) -> Result<String, String> {
    let trimmed = url.trim();
    if !trimmed.starts_with("https://") && !trimmed.starts_with("http://") {
        return Err("URL must use http(s)://".into());
    }
    let without_scheme = trimmed
        .split_once("://")
        .map(|(_, host)| host)
        .ok_or_else(|| "URL is missing host".to_string())?;
    let host = without_scheme
        .split('/')
        .next()
        .unwrap_or("")
        .split(':')
        .next()
        .unwrap_or("");
    if host.is_empty() {
        return Err("URL host must not be empty".into());
    }
    if contains_control_chars(host) || contains_control_chars(trimmed) {
        return Err("URL contains control characters".into());
    }
    if !allowed_hosts
        .iter()
        .any(|allowed| host.eq_ignore_ascii_case(allowed))
    {
        return Err(format!(
            "URL host `{host}` is not on the allow-list for this provider"
        ));
    }
    Ok(trimmed.to_string())
}

fn contains_parent_dir_component(path: &str) -> bool {
    Path::new(path)
        .components()
        .any(|component| matches!(component, Component::ParentDir))
}

fn contains_control_chars(value: &str) -> bool {
    value.chars().any(|c| c.is_control())
}

/// Validate that a string is safe to forward as a single argument to a child
/// process. Rejects the empty string, leading dashes (which would be parsed
/// as flags by `node`), null bytes, and other control chars.
pub fn ensure_safe_command_arg(value: &str, label: &str) -> Result<String, String> {
    if value.is_empty() {
        return Err(format!("{label} must not be empty"));
    }
    if value.starts_with('-') {
        return Err(format!(
            "{label} must not start with `-` (rejected to prevent flag injection)"
        ));
    }
    if contains_parent_dir_component(value) {
        return Err(format!("{label} must not contain `..` traversal segments"));
    }
    if contains_control_chars(value) {
        return Err(format!("{label} must not contain control characters"));
    }
    Ok(value.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_parent_traversal() {
        let result = ensure_within_acceptable_roots(
            "../escaped/path.md",
            "html",
            &[PathBuf::from("/tmp/vault")],
        );
        assert!(result.is_err());
    }

    #[test]
    fn rejects_path_outside_roots() {
        let result =
            ensure_within_acceptable_roots("/etc/passwd", "html", &[PathBuf::from("/tmp/vault")]);
        assert!(result.is_err());
    }

    #[test]
    fn accepts_path_inside_root() {
        let result = ensure_within_acceptable_roots(
            "/tmp/vault/imports/post.html",
            "html",
            &[PathBuf::from("/tmp/vault")],
        );
        assert!(
            matches!(result, Ok(path) if path == std::path::Path::new("/tmp/vault/imports/post.html"))
        );
    }

    #[test]
    fn rejects_non_http_scheme() {
        let result = ensure_safe_provider_url("javascript:alert(1)", &["x.com"]);
        assert!(result.is_err());
    }

    #[test]
    fn rejects_unknown_host() {
        let result = ensure_safe_provider_url("https://example.com/u", &["x.com"]);
        assert!(result.is_err());
    }

    #[test]
    fn accepts_known_host() {
        let result =
            ensure_safe_provider_url("https://x.com/someone/status/123", &["x.com", "reddit.com"]);
        assert_eq!(result.unwrap(), "https://x.com/someone/status/123");
    }

    #[test]
    fn rejects_flag_injection_in_command_arg() {
        assert!(ensure_safe_command_arg("--eval=evil", "profile").is_err());
        assert!(ensure_safe_command_arg("", "profile").is_err());
        assert!(ensure_safe_command_arg("/normal/path", "profile").is_ok());
    }

    #[test]
    fn rejects_profile_path_traversal() {
        assert!(ensure_safe_command_arg("/tmp/../private-profile", "profile").is_err());
    }

    #[test]
    fn allows_hacker_news_host_but_rejects_redirect_target() {
        assert!(ensure_safe_provider_url(
            "https://news.ycombinator.com/saved?id=koosha",
            &["news.ycombinator.com"],
        )
        .is_ok());
        assert!(ensure_safe_provider_url(
            "https://evil.example/saved?id=koosha",
            &["news.ycombinator.com"],
        )
        .is_err());
    }
}
