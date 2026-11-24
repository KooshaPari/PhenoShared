use super::{config::validate_id, Config};
use anyhow::{bail, Context, Result};
use reqwest::{
    header::{HeaderMap, HeaderValue, AUTHORIZATION},
    Method, Url,
};
use serde_json::{json, Value};
use std::{path::Path, time::Duration};

/// Credentials remain inside sensitive HTTP headers; errors never include bodies/tokens.
#[derive(Clone)]
pub struct DiscordClient {
    http: reqwest::Client,
    base: String,
    offline: bool,
}
impl std::fmt::Debug for DiscordClient {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DiscordClient").finish_non_exhaustive()
    }
}
impl DiscordClient {
    pub fn from_config(config: &Config) -> Result<Self> {
        config.validate()?;
        config.validate_board()?;
        Self::with_endpoint("https://discord.com/api/v10", &config.credential_file)
    }
    /// Loopback endpoint is an explicit offline-test seam; arbitrary credential destinations rejected.
    pub fn with_endpoint(base: &str, credential_file: &Path) -> Result<Self> {
        let url = Url::parse(base).context("invalid Discord API endpoint")?;
        let trusted = url.scheme() == "https"
            && url.host_str() == Some("discord.com")
            && url.path() == "/api/v10"
            && url.port_or_known_default() == Some(443);
        let local = url.scheme() == "http"
            && matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "[::1]"));
        if !trusted && !local {
            bail!("untrusted Discord API endpoint");
        }
        if !url.username().is_empty()
            || url.password().is_some()
            || url.query().is_some()
            || url.fragment().is_some()
        {
            bail!("invalid API endpoint credentials/query");
        }
        let token =
            std::fs::read_to_string(credential_file).context("Discord credential unavailable")?;
        if token.trim().is_empty() {
            bail!("empty Discord credential");
        }
        let mut headers = HeaderMap::new();
        let mut auth = HeaderValue::from_str(&format!("Bot {}", token.trim()))
            .map_err(|_| anyhow::anyhow!("invalid Discord credential"))?;
        auth.set_sensitive(true);
        headers.insert(AUTHORIZATION, auth);
        let http = reqwest::Client::builder()
            .default_headers(headers)
            .redirect(reqwest::redirect::Policy::none())
            .timeout(Duration::from_secs(8))
            .user_agent("Phinbox/0.9 Discord-management")
            .build()
            .context("HTTP client initialization failed")?;
        Ok(Self {
            http,
            base: base.trim_end_matches('/').into(),
            offline: local,
        })
    }
    pub async fn request(&self, method: Method, path: &str, body: Option<&Value>) -> Result<Value> {
        if !path.starts_with('/') || path.starts_with("//") || path.contains(['\r', '\n']) {
            bail!("invalid Discord route");
        }
        for attempt in 0..3 {
            let mut q = self
                .http
                .request(method.clone(), format!("{}{path}", self.base));
            if let Some(body) = body {
                q = q.json(body);
            }
            let response = q.send().await.map_err(|_| {
                anyhow::anyhow!("Discord transport failed; outcome may be ambiguous")
            })?;
            let status = response.status();
            if status.as_u16() == 429 {
                let value: Value = response.json().await.unwrap_or(Value::Null);
                let wait = value
                    .get("retry_after")
                    .and_then(Value::as_f64)
                    .unwrap_or(1.0);
                if !wait.is_finite() || !(0.0..=10.0).contains(&wait) || attempt == 2 {
                    bail!("Discord rate limit; retry later");
                }
                tokio::time::sleep(Duration::from_secs_f64(wait.max(0.05))).await;
                continue;
            }
            if !status.is_success() {
                bail!("Discord HTTP {}; response body withheld", status.as_u16());
            }
            if status.as_u16() == 204 {
                return Ok(Value::Null);
            }
            return response.json().await.map_err(|_| {
                anyhow::anyhow!("Discord response invalid; outcome may be ambiguous")
            });
        }
        bail!("Discord retry budget exhausted")
    }
    /// Full original and full workflow metadata travel as UTF-8 attachments, not clipped content.
    pub async fn request_item(
        &self,
        method: Method,
        path: &str,
        body: &Value,
        item: &crate::management::Item,
    ) -> Result<Value> {
        let mut payload = body.clone();
        let target = if payload.get("message").is_some() {
            payload
                .get_mut("message")
                .context("missing starter message")?
        } else {
            &mut payload
        };
        target["attachments"] =
            json!([{"id":0,"filename":"original.txt"},{"id":1,"filename":"workflow.json"}]);
        let metadata = json!({"id":item.id,"title":item.title,"status":item.status,"revision":item.revision,
            "lane":item.lane,"eta":item.eta,"assignee":item.assignee,"acknowledged":item.acknowledged});
        let metadata = serde_json::to_string_pretty(&metadata)?;
        if item.original.len() + metadata.len() > 8 * 1024 * 1024 {
            bail!("management item exceeds supported attachment size; original retained locally");
        }
        for attempt in 0..3 {
            let form = reqwest::multipart::Form::new()
                .text("payload_json", payload.to_string())
                .part(
                    "files[0]",
                    reqwest::multipart::Part::text(item.original.clone()).file_name("original.txt"),
                )
                .part(
                    "files[1]",
                    reqwest::multipart::Part::text(metadata.clone()).file_name("workflow.json"),
                );
            let response = self
                .http
                .request(method.clone(), format!("{}{path}", self.base))
                .multipart(form)
                .send()
                .await
                .map_err(|_| {
                    anyhow::anyhow!("Discord attachment transport failed; outcome may be ambiguous")
                })?;
            let status = response.status();
            if status.as_u16() == 429 {
                let value: Value = response.json().await.unwrap_or(Value::Null);
                let wait = value["retry_after"].as_f64().unwrap_or(1.0);
                if !wait.is_finite() || !(0.0..=10.0).contains(&wait) || attempt == 2 {
                    bail!("Discord rate limit; retry later");
                }
                tokio::time::sleep(Duration::from_secs_f64(wait.max(0.05))).await;
                continue;
            }
            if !status.is_success() {
                bail!(
                    "Discord HTTP {}; attachment response withheld",
                    status.as_u16()
                );
            }
            return response.json().await.map_err(|_| {
                anyhow::anyhow!("Discord attachment response invalid; outcome may be ambiguous")
            });
        }
        bail!("Discord attachment retry budget exhausted")
    }
    pub async fn verify(&self, config: &Config) -> Result<()> {
        config.validate()?;
        let user = self.request(Method::GET, "/users/@me", None).await?;
        let app = self
            .request(Method::GET, "/oauth2/applications/@me", None)
            .await?;
        if user["id"].as_str() != Some(&config.binding.application_id)
            || user["bot"] != true
            || app["id"].as_str() != Some(&config.binding.application_id)
        {
            bail!("credential identity differs from configured Instinct binding");
        }
        let forum = self
            .request(
                Method::GET,
                &format!("/channels/{}", config.binding.forum_id),
                None,
            )
            .await?;
        if forum["type"] != 15 || forum["guild_id"].as_str() != Some(&config.binding.guild_id) {
            bail!("Discord forum identity mismatch");
        }
        let tags = forum["available_tags"]
            .as_array()
            .context("Discord forum tags unavailable")?;
        for (name, id) in &config.tags {
            if !tags
                .iter()
                .any(|t| t["name"].as_str() == Some(name) && t["id"].as_str() == Some(id))
            {
                bail!("Discord configured status tags changed");
            }
        }
        Ok(())
    }
    pub async fn verify_thread(
        &self,
        config: &Config,
        map: &crate::management::ThreadMap,
    ) -> Result<()> {
        config.check_map(map)?;
        let t = self
            .request(Method::GET, &format!("/channels/{}", map.thread_id), None)
            .await?;
        if t["guild_id"].as_str() != Some(&config.binding.guild_id)
            || t["parent_id"].as_str() != Some(&config.binding.forum_id)
            || t["owner_id"].as_str() != Some(&config.binding.application_id)
        {
            bail!("remote thread owner/binding mismatch");
        }
        let m = self
            .request(
                Method::GET,
                &format!("/channels/{}/messages/{}", map.thread_id, map.message_id),
                None,
            )
            .await?;
        if m["author"]["id"].as_str() != Some(&config.binding.application_id) {
            bail!("remote starter message owner mismatch");
        }
        Ok(())
    }
    pub async fn acknowledge(&self, id: &str, token: &str) -> Result<()> {
        validate_id(id)?;
        if token.is_empty()
            || !token
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.'))
        {
            bail!("invalid interaction token");
        }
        // This separately bounded client call has to finish before the 3s deadline.
        tokio::time::timeout(
            Duration::from_millis(2000),
            self.request(
                Method::POST,
                &format!("/interactions/{id}/{token}/callback"),
                Some(&json!({"type":6})),
            ),
        )
        .await
        .context("Discord interaction acknowledgement deadline exceeded")??;
        Ok(())
    }
    pub async fn ephemeral(&self, application: &str, token: &str, content: &str) -> Result<()> {
        validate_id(application)?;
        if token.is_empty()
            || !token
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-' | b'.'))
        {
            bail!("invalid interaction token");
        }
        self.request(
            Method::POST,
            &format!("/webhooks/{application}/{token}"),
            Some(&json!({"content":content,"flags":64,"allowed_mentions":{"parse":[]}})),
        )
        .await?;
        Ok(())
    }
    pub async fn gateway_url(&self) -> Result<String> {
        let d = self.request(Method::GET, "/gateway/bot", None).await?;
        if d["session_start_limit"]["remaining"].as_u64() == Some(0) {
            bail!("Discord Gateway identify limit exhausted");
        }
        let raw = d["url"].as_str().context("Gateway URL missing")?;
        self.gateway_endpoint(raw)
    }
    pub(super) fn gateway_endpoint(&self, raw: &str) -> Result<String> {
        let url = Url::parse(raw).context("invalid Gateway URL")?;
        let production = url.scheme() == "wss"
            && url
                .host_str()
                .is_some_and(|h| h.starts_with("gateway") && h.ends_with(".discord.gg"));
        let local = self.offline
            && url.scheme() == "ws"
            && matches!(url.host_str(), Some("127.0.0.1" | "localhost" | "[::1]"));
        if !(production || local)
            || !url.username().is_empty()
            || url.password().is_some()
            || url.query().is_some()
            || url.fragment().is_some()
        {
            bail!("untrusted Gateway URL");
        }
        Ok(format!("{}/?v=10&encoding=json", raw.trim_end_matches('/')))
    }
    pub(super) fn gateway_token(path: &Path) -> Result<String> {
        std::fs::read_to_string(path)
            .map(|s| s.trim().to_string())
            .context("Gateway credential unavailable")
    }
}
