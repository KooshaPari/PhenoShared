use reqwest::{Client, StatusCode};
use scraper::Html;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::net::{IpAddr, SocketAddr, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::time::Duration;

pub const MAX_BYTES: usize = 1_000_000;
const TIMEOUT: Duration = Duration::from_secs(15);
const USER_AGENT: &str = "ResearchLedger/0.1 (+local-first research capture)";
const RETRY_BASE: Duration = Duration::from_secs(1);
const RETRY_MAX: Duration = Duration::from_secs(8);
const MAX_ATTEMPTS: usize = 3;

#[derive(Debug, Clone)]
pub struct FetchedReference {
    pub artifact_path: String,
    pub content_type: String,
    pub http_status: u16,
    pub byte_count: usize,
    pub content_hash: String,
    pub body: String,
}

#[derive(Debug, thiserror::Error)]
pub enum FetchError {
    #[error("unsafe reference URL: {0}")]
    UnsafeUrl(String),
    #[error("robots.txt disallows this URL")]
    RobotsDenied,
    #[error("reference request failed: {0}")]
    Request(#[from] reqwest::Error),
    #[error("reference returned unsupported content type: {0}")]
    UnsupportedContentType(String),
    #[error("reference exceeded {MAX_BYTES} byte limit")]
    TooLarge,
    #[error("reference body was not valid UTF-8")]
    InvalidUtf8,
    #[error("reference artifact write failed: {0}")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Clone)]
struct ResolvedTarget {
    url: url::Url,
    host: String,
    addrs: Vec<SocketAddr>,
}

/// Small in-process domain budget. The worker is currently deliberately
/// bounded, but keeping this accounting at the fetch boundary makes it safe
/// to add parallel jobs without changing the SSRF/robots policy.
#[derive(Debug, Default)]
pub struct DomainConcurrency {
    active: HashMap<String, usize>,
    limit: usize,
}

impl DomainConcurrency {
    pub fn new(limit: usize) -> Self {
        Self {
            active: HashMap::new(),
            limit: limit.max(1),
        }
    }

    pub fn try_acquire(&mut self, raw_url: &str) -> bool {
        let Ok(url) = url::Url::parse(raw_url) else {
            return false;
        };
        let Some(domain) = url.host_str() else {
            return false;
        };
        let active = self.active.entry(domain.to_ascii_lowercase()).or_default();
        if *active >= self.limit {
            return false;
        }
        *active += 1;
        true
    }

    pub fn release(&mut self, raw_url: &str) {
        let Ok(url) = url::Url::parse(raw_url) else {
            return;
        };
        let Some(domain) = url.host_str() else { return };
        let key = domain.to_ascii_lowercase();
        if let Some(active) = self.active.get_mut(&key) {
            *active = active.saturating_sub(1);
            if *active == 0 {
                self.active.remove(&key);
            }
        }
    }

    #[cfg(test)]
    pub fn active_for(&self, raw_url: &str) -> usize {
        let Ok(url) = url::Url::parse(raw_url) else {
            return 0;
        };
        url.host_str()
            .and_then(|host| self.active.get(&host.to_ascii_lowercase()).copied())
            .unwrap_or(0)
    }
}

pub fn retry_delay(attempt: u32) -> Duration {
    let exponent = attempt.min(3);
    (RETRY_BASE * 2u32.pow(exponent)).min(RETRY_MAX)
}

pub fn retryable(error: &FetchError) -> bool {
    matches!(error, FetchError::Request(_))
}

#[cfg(test)]
fn validate_public_url(raw: &str) -> Result<url::Url, FetchError> {
    Ok(resolve_public_url(raw)?.url)
}

fn resolve_public_url(raw: &str) -> Result<ResolvedTarget, FetchError> {
    let url = url::Url::parse(raw).map_err(|error| FetchError::UnsafeUrl(error.to_string()))?;
    if !matches!(url.scheme(), "http" | "https") {
        return Err(FetchError::UnsafeUrl(
            "only http and https are allowed".into(),
        ));
    }
    if url.username() != "" || url.password().is_some() {
        return Err(FetchError::UnsafeUrl("userinfo is not allowed".into()));
    }
    let host = url
        .host_str()
        .ok_or_else(|| FetchError::UnsafeUrl("host is required".into()))?
        .to_ascii_lowercase();
    if host == "localhost" || host.ends_with(".localhost") {
        return Err(FetchError::UnsafeUrl("localhost is not allowed".into()));
    }
    let port = url.port_or_known_default().unwrap_or(443);
    let literal_host = host.trim_matches(['[', ']']);
    let addrs = if let Ok(ip) = literal_host.parse::<IpAddr>() {
        vec![SocketAddr::new(ip, 0)]
    } else {
        let resolved = (host.as_str(), port)
            .to_socket_addrs()
            .map_err(|error| FetchError::UnsafeUrl(format!("host could not be resolved: {error}")))?
            .map(|address| SocketAddr::new(address.ip(), 0))
            .collect::<Vec<_>>();
        if resolved.is_empty() {
            return Err(FetchError::UnsafeUrl(
                "host did not resolve to an address".into(),
            ));
        }
        resolved
    };
    if addrs
        .iter()
        .any(|address| is_private_or_local(address.ip()))
    {
        return Err(FetchError::UnsafeUrl(
            "host resolves to a private or local address".into(),
        ));
    }
    Ok(ResolvedTarget { url, host, addrs })
}

fn is_private_or_local(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ip) => {
            let [first, second, third, _] = ip.octets();
            ip.is_loopback()
                || ip.is_private()
                || ip.is_link_local()
                || ip.is_unspecified()
                || (first == 0)
                || (first == 100 && (64..=127).contains(&second))
                || (first == 192 && second == 0 && (third == 0 || third == 1 || third == 2))
                || (first == 198 && (second == 18 || second == 19))
                || (first == 198 && second == 51 && third == 100)
                || (first == 203 && second == 0 && third == 113)
                || first >= 224
        }
        IpAddr::V6(ip) => {
            ip.to_ipv4_mapped()
                .is_some_and(|mapped| is_private_or_local(IpAddr::V4(mapped)))
                || ip.is_loopback()
                || ip.is_unspecified()
                || ip.is_unique_local()
                || ip.is_unicast_link_local()
                || ip.is_multicast()
        }
    }
}

pub fn robots_allows(body: &str, path: &str) -> bool {
    let mut applies = false;
    let mut allowed = true;
    for line in body.lines() {
        let line = line.split('#').next().unwrap_or("").trim();
        let Some((field, value)) = line.split_once(':') else {
            continue;
        };
        match field.trim().to_ascii_lowercase().as_str() {
            "user-agent" => applies = value.trim() == "*",
            "disallow" if applies => {
                let rule = value.trim();
                if !rule.is_empty() && path.starts_with(rule) {
                    allowed = false;
                }
            }
            "allow" if applies => {
                let rule = value.trim();
                if !rule.is_empty() && path.starts_with(rule) {
                    allowed = true;
                }
            }
            _ => {}
        }
    }
    allowed
}

async fn read_bounded(mut response: reqwest::Response) -> Result<Vec<u8>, FetchError> {
    if response
        .content_length()
        .is_some_and(|length| length > MAX_BYTES as u64)
    {
        return Err(FetchError::TooLarge);
    }
    let mut bytes = Vec::new();
    while let Some(chunk) = response.chunk().await? {
        if bytes.len().saturating_add(chunk.len()) > MAX_BYTES {
            return Err(FetchError::TooLarge);
        }
        bytes.extend_from_slice(&chunk);
    }
    Ok(bytes)
}

pub async fn fetch(raw_url: &str) -> Result<FetchedReference, FetchError> {
    let target = resolve_public_url(raw_url)?;
    let client = pinned_client(&target)?;
    let robots_url = target
        .url
        .join("/robots.txt")
        .map_err(|error| FetchError::UnsafeUrl(error.to_string()))?;
    let robots = client.get(robots_url).send().await?;
    if robots.status().is_success() {
        let robots_body =
            String::from_utf8(read_bounded(robots).await?).map_err(|_| FetchError::InvalidUtf8)?;
        if !robots_allows(&robots_body, target.url.path()) {
            return Err(FetchError::RobotsDenied);
        }
    } else if robots.status() != StatusCode::NOT_FOUND {
        return Err(FetchError::Request(robots.error_for_status().unwrap_err()));
    }

    let response = client
        .get(target.url.clone())
        .send()
        .await?
        .error_for_status()?;
    let status = response.status().as_u16();
    let content_type = response
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .unwrap_or("text/plain")
        .split(';')
        .next()
        .unwrap_or("text/plain")
        .trim()
        .to_string();
    if !(content_type.starts_with("text/")
        || matches!(
            content_type.as_str(),
            "application/json" | "application/xml" | "application/xhtml+xml"
        ))
    {
        return Err(FetchError::UnsupportedContentType(content_type));
    }
    let bytes = read_bounded(response).await?;
    let body = String::from_utf8(bytes.clone()).map_err(|_| FetchError::InvalidUtf8)?;
    let content_hash = format!("{:x}", Sha256::digest(&bytes));
    Ok(FetchedReference {
        artifact_path: format!(".researchledger/references/{content_hash}.txt"),
        content_type,
        http_status: status,
        byte_count: bytes.len(),
        content_hash,
        body,
    })
}

/// Retry transient request failures with bounded exponential backoff. Policy,
/// robots, content-type, and byte-limit failures remain deterministic.
pub async fn fetch_with_retry(raw_url: &str) -> Result<FetchedReference, FetchError> {
    let mut last_error = None;
    for attempt in 0..MAX_ATTEMPTS {
        match fetch(raw_url).await {
            Ok(result) => return Ok(result),
            Err(error) if retryable(&error) && attempt + 1 < MAX_ATTEMPTS => {
                last_error = Some(error);
                tokio::time::sleep(retry_delay(attempt as u32)).await;
            }
            Err(error) => return Err(error),
        }
    }
    Err(last_error.expect("retry loop records a transient failure"))
}

fn pinned_client(target: &ResolvedTarget) -> Result<Client, FetchError> {
    Client::builder()
        .user_agent(USER_AGENT)
        .timeout(TIMEOUT)
        .no_proxy()
        .resolve_to_addrs(&target.host, &target.addrs)
        .redirect(reqwest::redirect::Policy::none())
        .build()
        .map_err(FetchError::Request)
}

pub fn write_artifact(root: &Path, fetched: &FetchedReference) -> Result<PathBuf, FetchError> {
    let path = root.join(&fetched.artifact_path);
    let parent = path
        .parent()
        .ok_or_else(|| std::io::Error::other("artifact has no parent"))?;
    std::fs::create_dir_all(parent)?;
    let temp = path.with_extension("tmp");
    std::fs::write(&temp, fetched.body.as_bytes())?;
    std::fs::rename(&temp, &path)?;
    Ok(path)
}

pub fn extract_text(body: &str, content_type: &str) -> String {
    if content_type == "text/html" || content_type == "application/xhtml+xml" {
        Html::parse_document(body)
            .root_element()
            .text()
            .collect::<Vec<_>>()
            .join(" ")
    } else {
        body.to_string()
    }
}

pub fn render_markdown(url: &str, fetched: &FetchedReference) -> String {
    let text = extract_text(&fetched.body, &fetched.content_type);
    let resource = serde_json::to_string(url).expect("serializing a URL string is infallible");
    format!(
        "---\ntype: \"Fetched Reference\"\ntitle: \"Fetched reference\"\nresource: {resource}\ntimestamp: {}\ntags: [reference, fetched]\n---\n\n# Captured Reference\n\n{text}\n\n# Citations\n\n[1] [Original reference]({url})\n",
        chrono::Utc::now().to_rfc3339(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_private_and_credentialed_urls() {
        assert!(validate_public_url("http://127.0.0.1:8000/a").is_err());
        assert!(validate_public_url("http://[::ffff:127.0.0.1]/a").is_err());
        assert!(validate_public_url("http://[ff02::1]/a").is_err());
        assert!(validate_public_url("http://100.64.0.1/a").is_err());
        assert!(validate_public_url("http://192.0.1.0/a").is_err());
        assert!(validate_public_url("http://192.0.2.1/a").is_err());
        assert!(validate_public_url("http://224.0.0.1/a").is_err());
        assert!(validate_public_url("http://255.255.255.255/a").is_err());
        assert!(validate_public_url("https://user:pass@example.com/a").is_err());
        assert!(validate_public_url("file:///tmp/a").is_err());
    }

    #[test]
    fn rejects_hosts_that_cannot_be_resolved_before_fetching() {
        assert!(validate_public_url("https://does-not-resolve.invalid/research").is_err());
    }

    #[test]
    fn robots_rules_are_deterministic() {
        let robots = "User-agent: *\nDisallow: /private\nAllow: /private/public";
        assert!(!robots_allows(robots, "/private/secret"));
        assert!(robots_allows(robots, "/private/public/item"));
        assert!(robots_allows(robots, "/public"));
    }

    #[test]
    fn html_is_reduced_to_readable_text() {
        assert_eq!(
            extract_text("<h1>Hello</h1><p>World</p>", "text/html"),
            "Hello World"
        );
    }

    #[test]
    fn reference_frontmatter_quotes_the_resource_url() {
        let fetched = FetchedReference {
            artifact_path: ".researchledger/references/hash.txt".into(),
            content_type: "text/plain".into(),
            http_status: 200,
            byte_count: 4,
            content_hash: "hash".into(),
            body: "body".into(),
        };
        let markdown = render_markdown("https://example.com/a?title=What%3A%20now", &fetched);
        assert!(markdown.contains("resource: \"https://example.com/a?title=What%3A%20now\""));
    }

    #[test]
    fn retry_policy_only_retries_transient_requests() {
        assert!(retryable(&FetchError::Request(
            reqwest::Client::new().get("http://[").build().unwrap_err()
        )));
        assert!(!retryable(&FetchError::RobotsDenied));
        assert!(!retryable(&FetchError::TooLarge));
    }

    #[test]
    fn domain_budget_is_accounted_and_bounded() {
        let mut budget = DomainConcurrency::new(1);
        assert!(budget.try_acquire("https://Example.com/a"));
        assert_eq!(budget.active_for("https://example.com/b"), 1);
        assert!(!budget.try_acquire("https://example.com/c"));
        budget.release("https://example.com/a");
        assert!(budget.try_acquire("https://example.com/c"));
    }

    #[test]
    fn retry_backoff_is_exponential_and_bounded() {
        assert_eq!(retry_delay(0), Duration::from_secs(1));
        assert_eq!(retry_delay(1), Duration::from_secs(2));
        assert_eq!(retry_delay(99), RETRY_MAX);
    }
}
