use base64::Engine;
use reqwest::{header, Client, StatusCode};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct StarredRepository {
    pub name: String,
    pub full_name: String,
    pub description: Option<String>,
    pub html_url: String,
    pub default_branch: String,
    pub language: Option<String>,
    pub topics: Vec<String>,
    pub owner: RepositoryOwner,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct RepositoryOwner {
    pub login: String,
}

#[derive(Debug, Deserialize)]
struct ReadmeResponse {
    content: String,
    encoding: String,
}

#[derive(Debug)]
pub enum GithubError {
    Http(reqwest::Error),
    RateLimited,
    InvalidResponse(String),
    Decode(String),
}

impl std::fmt::Display for GithubError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Http(error) => write!(formatter, "GitHub request failed: {error}"),
            Self::RateLimited => write!(formatter, "GitHub rate limit exceeded"),
            Self::InvalidResponse(status) => write!(formatter, "GitHub returned {status}"),
            Self::Decode(message) => write!(formatter, "GitHub README decode failed: {message}"),
        }
    }
}

impl std::error::Error for GithubError {}

pub struct GithubClient {
    client: Client,
    token: String,
}

impl GithubClient {
    pub fn new(token: impl Into<String>) -> Result<Self, GithubError> {
        let mut headers = header::HeaderMap::new();
        headers.insert(
            header::ACCEPT,
            header::HeaderValue::from_static("application/vnd.github+json"),
        );
        headers.insert(
            "x-github-api-version",
            header::HeaderValue::from_static("2022-11-28"),
        );
        let client = Client::builder()
            .default_headers(headers)
            .user_agent("ResearchLedger/0.1")
            .build()
            .map_err(GithubError::Http)?;
        Ok(Self {
            client,
            token: token.into(),
        })
    }

    pub async fn list_starred(&self) -> Result<Vec<StarredRepository>, GithubError> {
        let mut page = 1;
        let mut repositories = Vec::new();
        loop {
            let response = self
                .client
                .get("https://api.github.com/user/starred")
                .bearer_auth(&self.token)
                .query(&[("per_page", 100), ("page", page)])
                .send()
                .await
                .map_err(GithubError::Http)?;
            if response.status() == StatusCode::FORBIDDEN {
                return Err(GithubError::RateLimited);
            }
            if !response.status().is_success() {
                return Err(GithubError::InvalidResponse(response.status().to_string()));
            }
            let batch: Vec<StarredRepository> = response.json().await.map_err(GithubError::Http)?;
            let done = batch.len() < 100;
            repositories.extend(batch);
            if done {
                return Ok(repositories);
            }
            page += 1;
        }
    }

    pub async fn read_readme(
        &self,
        owner: &str,
        repo: &str,
    ) -> Result<Option<String>, GithubError> {
        let response = self
            .client
            .get(format!(
                "https://api.github.com/repos/{owner}/{repo}/readme"
            ))
            .bearer_auth(&self.token)
            .send()
            .await
            .map_err(GithubError::Http)?;
        if response.status() == StatusCode::NOT_FOUND {
            return Ok(None);
        }
        if response.status() == StatusCode::FORBIDDEN {
            return Err(GithubError::RateLimited);
        }
        if !response.status().is_success() {
            return Err(GithubError::InvalidResponse(response.status().to_string()));
        }
        let payload: ReadmeResponse = response.json().await.map_err(GithubError::Http)?;
        if payload.encoding != "base64" {
            return Err(GithubError::Decode(format!(
                "unsupported README encoding: {}",
                payload.encoding
            )));
        }
        let normalized = payload.content.replace('\n', "");
        base64::engine::general_purpose::STANDARD
            .decode(normalized)
            .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
            .map(Some)
            .map_err(|error| GithubError::Decode(error.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decodes_github_readme_payload() {
        let value = base64::engine::general_purpose::STANDARD.encode("# Hello\n");
        let decoded = base64::engine::general_purpose::STANDARD
            .decode(value)
            .unwrap();
        assert_eq!(String::from_utf8(decoded).unwrap(), "# Hello\n");
    }
}
