//! User-initiated release availability check (no download or install).
//!
//! Compares the installed `sl-daemon` version to the latest GitHub Release tag.
//! Automatic background updates remain out of scope per ADR 0001.

use std::cmp::Ordering;

/// Default GitHub repository for release lookups.
pub const DEFAULT_REPO: &str = "KooshaPari/SessionLedger";

const GITHUB_API_BASE: &str = "https://api.github.com";

/// Outcome of comparing installed vs latest release versions.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum UpdateStatus {
    /// Installed version is at or above the latest published release.
    UpToDate { installed: String, latest: String },
    /// A newer release tag exists on GitHub.
    UpdateAvailable { installed: String, latest: String },
}

impl UpdateStatus {
    pub fn is_update_available(&self) -> bool {
        matches!(self, Self::UpdateAvailable { .. })
    }
}

/// Errors while resolving or comparing release metadata.
#[derive(Debug, thiserror::Error)]
pub enum UpdateCheckError {
    #[error("network: {0}")]
    Network(#[from] reqwest::Error),
    #[error("parse: {0}")]
    Parse(String),
}

/// Strip a leading `v` and surrounding whitespace from a release tag.
pub fn normalize_tag(tag: &str) -> &str {
    tag.trim().strip_prefix('v').unwrap_or(tag.trim())
}

/// Parse `major.minor.patch` with optional pre-release suffix ignored for ordering.
fn parse_semver(tag: &str) -> (u64, u64, u64) {
    let core = normalize_tag(tag).split('-').next().unwrap_or("");
    let mut parts = core.split('.');
    let major = parts.next().and_then(|p| p.parse().ok()).unwrap_or(0);
    let minor = parts.next().and_then(|p| p.parse().ok()).unwrap_or(0);
    let patch = parts.next().and_then(|p| p.parse().ok()).unwrap_or(0);
    (major, minor, patch)
}

/// Compare two release tags using semver ordering when possible.
pub fn version_cmp(a: &str, b: &str) -> Ordering {
    parse_semver(a).cmp(&parse_semver(b))
}

/// Compare installed version against a latest release tag.
pub fn compare_versions(installed: &str, latest_tag: &str) -> UpdateStatus {
    let installed = installed.trim().to_owned();
    let latest = latest_tag.trim().to_owned();
    if version_cmp(&installed, &latest) == Ordering::Less {
        UpdateStatus::UpdateAvailable { installed, latest }
    } else {
        UpdateStatus::UpToDate { installed, latest }
    }
}

/// Fetch the latest release tag from the GitHub REST API.
pub async fn fetch_latest_release_tag(
    client: &reqwest::Client,
    repo: &str,
) -> Result<String, UpdateCheckError> {
    let url = format!("{GITHUB_API_BASE}/repos/{repo}/releases/latest");
    let resp = client
        .get(&url)
        .header("Accept", "application/vnd.github+json")
        .header("X-GitHub-Api-Version", "2022-11-28")
        .header("User-Agent", "sl-daemon-check-update")
        .send()
        .await?;
    if !resp.status().is_success() {
        return Err(UpdateCheckError::Parse(format!("GitHub API returned HTTP {}", resp.status())));
    }
    let body: serde_json::Value = resp.json().await?;
    body.get("tag_name")
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|tag| !tag.is_empty())
        .map(str::to_owned)
        .ok_or_else(|| UpdateCheckError::Parse("missing tag_name in GitHub response".into()))
}

/// Human-readable summary for stdout.
pub fn format_status(status: &UpdateStatus) -> String {
    match status {
        UpdateStatus::UpToDate { installed, latest } => {
            format!("sl-daemon {installed} is up to date (latest release: {latest})")
        }
        UpdateStatus::UpdateAvailable { installed, latest } => {
            format!(
                "update available: sl-daemon {installed} → {latest}\n\
                 Download from https://github.com/{DEFAULT_REPO}/releases/tag/{latest}\n\
                 Verify SHA256SUMS (and Sigstore bundle when present) before replacing binaries."
            )
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_tag_strips_v_prefix() {
        assert_eq!(normalize_tag("v0.2.0"), "0.2.0");
        assert_eq!(normalize_tag("0.1.0"), "0.1.0");
    }

    #[test]
    fn version_cmp_orders_semver() {
        assert_eq!(version_cmp("0.1.0", "0.2.0"), Ordering::Less);
        assert_eq!(version_cmp("v0.2.0", "0.2.0"), Ordering::Equal);
        assert_eq!(version_cmp("1.0.0", "0.9.9"), Ordering::Greater);
    }

    #[test]
    fn compare_versions_detects_update_available() {
        let status = compare_versions("0.1.0", "v0.2.0");
        assert!(status.is_update_available());
    }

    #[test]
    fn compare_versions_reports_up_to_date() {
        let status = compare_versions("0.2.0", "v0.2.0");
        assert!(!status.is_update_available());
        let status = compare_versions("0.3.0", "v0.2.0");
        assert!(!status.is_update_available());
    }
}
