//! Runtime selection of `SemanticMemoryPort` adapter implementations.
//!
//! Defaults to the portable JSONL adapter so existing call sites keep
//! working without configuration. Remote adapters (Supermemory / Letta /
//! Cognee) are picked explicitly by name in higher-level wiring code.

use std::path::PathBuf;

use forge_domain::{SemanticMemoryError, SemanticMemoryPort};
use serde::{Deserialize, Serialize};

use crate::{
    JsonlSemanticMemory,
    cognee::{COGNEE_API_KEY_ENV, COGNEE_BASE_URL_ENV, COGNEE_DATASET_ENV, CogneeAdapter},
    letta::{LETTA_AGENT_ID_ENV, LETTA_API_KEY_ENV, LETTA_BASE_URL_ENV, LettaAdapter},
    supermemory::{SUPERMEMORY_API_KEY_ENV, SUPERMEMORY_BASE_URL_ENV, SupermemoryAdapter},
};

/// Environment variable that selects which `SemanticMemoryPort` adapter
/// backs the runtime. Accepts one of the `AdapterKind` lowercase labels
/// (`jsonl`, `supermemory`, `letta`, `cognee`). Defaults to `jsonl` when
/// unset so the existing call sites keep working without configuration.
pub const FORGE_SEMANTIC_ADAPTER_ENV: &str = "FORGE_SEMANTIC_ADAPTER";

/// Selects which `SemanticMemoryPort` adapter backs a given semantic-memory
/// client at runtime.
///
/// Default is `Jsonl` for backward compatibility — the JSONL adapter was the
/// only one available before P3.4, and keeping it as the default avoids
/// silently routing traffic at a remote provider when callers do not opt in.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AdapterKind {
    /// Portable, file-backed reference adapter (P1.5). No network access.
    #[default]
    Jsonl,
    /// Supermemory Cloud adapter (`api.supermemory.ai`). Requires `SUPERMEMORY_API_KEY`.
    Supermemory,
    /// Letta Cloud or self-hosted adapter. Requires `LETTA_API_KEY`.
    Letta,
    /// Cognee Cloud or self-hosted adapter. Requires `COGNEE_API_KEY`.
    Cognee,
}

impl AdapterKind {
    /// Stable string label suitable for diagnostics and config files.
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Jsonl => "jsonl",
            Self::Supermemory => "supermemory",
            Self::Letta => "letta",
            Self::Cognee => "cognee",
        }
    }

    /// Parse an `AdapterKind` from a user-supplied label. Unknown labels
    /// fall back to `Jsonl` and the caller is expected to print a hint;
    /// the same fallback is used by [`Self::from_env`] for unset env vars.
    pub fn parse(label: &str) -> Self {
        match label.trim().to_ascii_lowercase().as_str() {
            "supermemory" => Self::Supermemory,
            "letta" => Self::Letta,
            "cognee" => Self::Cognee,
            // "jsonl" and any unknown value (including empty) fall back
            // to the default. This keeps the runtime usable even when a
            // bad config file is dropped on disk.
            _ => Self::Jsonl,
        }
    }

    /// Reads `FORGE_SEMANTIC_ADAPTER` from the process environment and
    /// returns the corresponding `AdapterKind`. Falls back to `Jsonl`
    /// when the env var is unset or holds an unknown value.
    pub fn from_env() -> Self {
        match std::env::var(FORGE_SEMANTIC_ADAPTER_ENV) {
            Err(_) => Self::default(),
            Ok(label) => Self::parse(&label),
        }
    }
}

impl core::fmt::Display for AdapterKind {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        formatter.write_str(self.as_str())
    }
}

/// Resolved runtime configuration for the `forge_semantic` adapter stack.
///
/// `Config` is the single entry point higher-level wiring code uses to
/// pick and build a `SemanticMemoryPort`. It reads from environment
/// variables in [`Self::from_env`], can be constructed manually for tests,
/// and validates the resolved settings before [`Self::build`] returns a
/// usable adapter.
#[derive(Debug, Clone)]
pub struct Config {
    /// Which adapter this configuration selects.
    pub kind: AdapterKind,
    /// File path the JSONL adapter opens when `kind == Jsonl`. Ignored
    /// by the remote adapters. Defaults to
    /// `<workspace>/.forge/semantic_memory.jsonl` via [`Self::from_env`].
    pub jsonl_path: Option<PathBuf>,
    /// Cognee-specific configuration. Required when `kind == Cognee`.
    pub cognee: Option<CogneeConfig>,
    /// Letta-specific configuration. Required when `kind == Letta`.
    pub letta: Option<LettaConfig>,
    /// Supermemory-specific configuration. Required when `kind == Supermemory`.
    pub supermemory: Option<SupermemoryConfig>,
}

/// Cognee adapter configuration block.
#[derive(Debug, Clone)]
pub struct CogneeConfig {
    /// Bearer token for `Authorization: Bearer <key>`. Required.
    pub api_key: String,
    /// Base URL of the Cognee deployment (no trailing path). Defaults to
    /// the Cognee Cloud URL when empty.
    pub base_url: String,
    /// Cognee dataset name. All writes are scoped to this dataset.
    pub dataset: String,
}

/// Letta adapter configuration block.
#[derive(Debug, Clone)]
pub struct LettaConfig {
    /// Bearer token for `Authorization: Bearer <key>`. Required.
    pub api_key: String,
    /// Base URL of the Letta deployment (no trailing path). Defaults to
    /// the Letta Cloud URL when empty.
    pub base_url: String,
    /// Default Letta agent id used for store/recall/forget.
    pub default_agent_id: String,
}

/// Supermemory adapter configuration block.
#[derive(Debug, Clone)]
pub struct SupermemoryConfig {
    /// Bearer token for `Authorization: Bearer <key>`. Required.
    pub api_key: String,
    /// Base URL of the Supermemory deployment (no trailing path). Defaults
    /// to the Supermemory Cloud URL when empty.
    pub base_url: String,
}

impl Config {
    /// Reads the full adapter configuration from the process environment.
    ///
    /// - `FORGE_SEMANTIC_ADAPTER` selects the adapter kind.
    /// - The remote adapters read their respective `*_API_KEY`,
    ///   `*_BASE_URL` / `*_API_URL`, and dataset / agent env vars.
    /// - `FORGE_SEMANTIC_JSONL_PATH` overrides the JSONL file path.
    ///
    /// # Errors
    /// Returns `Backend { status: 401, ... }` if the chosen remote adapter
    /// has no API key. Validation errors surface through [`Self::validate`].
    pub fn from_env() -> Result<Self, SemanticMemoryError> {
        let kind = AdapterKind::from_env();
        let jsonl_path = std::env::var("FORGE_SEMANTIC_JSONL_PATH")
            .ok()
            .map(PathBuf::from);

        let cognee = if matches!(kind, AdapterKind::Cognee) {
            let api_key = std::env::var(COGNEE_API_KEY_ENV).unwrap_or_default();
            let base_url = std::env::var(COGNEE_BASE_URL_ENV)
                .unwrap_or_else(|_| crate::cognee::COGNEE_DEFAULT_BASE_URL.to_string());
            let dataset = std::env::var(COGNEE_DATASET_ENV)
                .unwrap_or_else(|_| "cognee-default-dataset".to_string());
            Some(CogneeConfig { api_key, base_url, dataset })
        } else {
            None
        };

        let letta = if matches!(kind, AdapterKind::Letta) {
            let api_key = std::env::var(LETTA_API_KEY_ENV).unwrap_or_default();
            let base_url = std::env::var(LETTA_BASE_URL_ENV)
                .unwrap_or_else(|_| crate::letta::LETTA_DEFAULT_BASE_URL.to_string());
            let default_agent_id = std::env::var(LETTA_AGENT_ID_ENV)
                .unwrap_or_else(|_| "letta-default-agent".to_string());
            Some(LettaConfig { api_key, base_url, default_agent_id })
        } else {
            None
        };

        let supermemory = if matches!(kind, AdapterKind::Supermemory) {
            let api_key = std::env::var(SUPERMEMORY_API_KEY_ENV).unwrap_or_default();
            let base_url = std::env::var(SUPERMEMORY_BASE_URL_ENV)
                .unwrap_or_else(|_| crate::supermemory::SUPERMEMORY_DEFAULT_BASE_URL.to_string());
            Some(SupermemoryConfig { api_key, base_url })
        } else {
            None
        };

        Ok(Self { kind, jsonl_path, cognee, letta, supermemory })
    }

    /// Constructs a configuration that resolves to the portable JSONL
    /// adapter with no remote credentials. Useful for unit tests and for
    /// the default boot path when no `FORGE_SEMANTIC_ADAPTER` is set.
    pub fn jsonl_default() -> Self {
        Self {
            kind: AdapterKind::Jsonl,
            jsonl_path: None,
            cognee: None,
            letta: None,
            supermemory: None,
        }
    }

    /// Validates that the configuration is internally consistent.
    ///
    /// # Errors
    /// - Returns `Backend { status: 401, ... }` when a remote adapter is
    ///   selected with no API key.
    /// - Returns `InvalidResponse` when a base URL cannot be parsed as
    ///   an HTTP/HTTPS URL.
    pub fn validate(&self) -> Result<(), SemanticMemoryError> {
        match self.kind {
            AdapterKind::Jsonl => Ok(()),
            AdapterKind::Supermemory => {
                let cfg = self.supermemory.as_ref().ok_or_else(|| {
                    SemanticMemoryError::InvalidResponse("supermemory config missing".to_string())
                })?;
                if cfg.api_key.trim().is_empty() {
                    return Err(SemanticMemoryError::Backend {
                        status: 401,
                        body: "missing SUPERMEMORY_API_KEY".to_string(),
                    });
                }
                validate_http_url(&cfg.base_url, "SUPERMEMORY_BASE_URL")?;
                Ok(())
            }
            AdapterKind::Letta => {
                let cfg = self.letta.as_ref().ok_or_else(|| {
                    SemanticMemoryError::InvalidResponse("letta config missing".to_string())
                })?;
                if cfg.api_key.trim().is_empty() {
                    return Err(SemanticMemoryError::Backend {
                        status: 401,
                        body: "missing LETTA_API_KEY".to_string(),
                    });
                }
                validate_http_url(&cfg.base_url, "LETTA_BASE_URL")?;
                Ok(())
            }
            AdapterKind::Cognee => {
                let cfg = self.cognee.as_ref().ok_or_else(|| {
                    SemanticMemoryError::InvalidResponse("cognee config missing".to_string())
                })?;
                if cfg.api_key.trim().is_empty() {
                    return Err(SemanticMemoryError::Backend {
                        status: 401,
                        body: "missing COGNEE_API_KEY".to_string(),
                    });
                }
                validate_http_url(&cfg.base_url, "COGNEE_API_URL")?;
                Ok(())
            }
        }
    }

    /// Builds the adapter selected by `self.kind` and returns it as a
    /// boxed trait object.
    ///
    /// # Errors
    /// Surfaces `validate()` failures and adapter-construction failures
    /// (e.g. unreachable URLs, malformed headers). For the JSONL adapter
    /// this is the only place where a missing path is resolved to the
    /// default `semantic_memory.jsonl` location.
    pub fn build(&self) -> Result<Box<dyn SemanticMemoryPort>, SemanticMemoryError> {
        self.validate()?;
        match self.kind {
            AdapterKind::Jsonl => {
                let path = self
                    .jsonl_path
                    .clone()
                    .unwrap_or_else(|| PathBuf::from("semantic_memory.jsonl"));
                let port = JsonlSemanticMemory::open(&path).map_err(|err| {
                    SemanticMemoryError::Unavailable(format!("jsonl adapter: {err}"))
                })?;
                Ok(Box::new(port))
            }
            AdapterKind::Supermemory => {
                // `validate()` ensures this is `Some`.
                let cfg = self.supermemory.as_ref().expect("validated");
                let adapter = SupermemoryAdapter::new(cfg.base_url.clone(), cfg.api_key.clone())?;
                Ok(Box::new(adapter))
            }
            AdapterKind::Letta => {
                let cfg = self.letta.as_ref().expect("validated");
                let adapter = LettaAdapter::new(
                    cfg.base_url.clone(),
                    cfg.api_key.clone(),
                    cfg.default_agent_id.clone(),
                )?;
                Ok(Box::new(adapter))
            }
            AdapterKind::Cognee => {
                let cfg = self.cognee.as_ref().expect("validated");
                let adapter = CogneeAdapter::new(
                    cfg.base_url.clone(),
                    cfg.api_key.clone(),
                    cfg.dataset.clone(),
                )?;
                Ok(Box::new(adapter))
            }
        }
    }
}

/// Validates that a base URL parses as `http://` or `https://`. Other
/// schemes (e.g. `file:`, `data:`) are rejected so a misconfigured
/// environment variable cannot trick the adapter into talking to the
/// wrong endpoint.
fn validate_http_url(value: &str, var_name: &'static str) -> Result<(), SemanticMemoryError> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Err(SemanticMemoryError::InvalidResponse(format!(
            "{var_name} must not be blank"
        )));
    }
    let url = reqwest::Url::parse(trimmed).map_err(|err| {
        SemanticMemoryError::InvalidResponse(format!("{var_name} not a valid URL: {err}"))
    })?;
    match url.scheme() {
        "http" | "https" => Ok(()),
        other => Err(SemanticMemoryError::InvalidResponse(format!(
            "{var_name} must be http:// or https://, got {other}://"
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_is_jsonl_for_backward_compat() {
        assert_eq!(AdapterKind::default(), AdapterKind::Jsonl);
    }

    #[test]
    fn adapter_kind_round_trips_through_serde() {
        for kind in [
            AdapterKind::Jsonl,
            AdapterKind::Supermemory,
            AdapterKind::Letta,
            AdapterKind::Cognee,
        ] {
            let serialized = serde_json::to_string(&kind).unwrap();
            let deserialized: AdapterKind = serde_json::from_str(&serialized).unwrap();
            assert_eq!(kind, deserialized);
        }
    }

    #[test]
    fn adapter_kind_has_stable_string_labels() {
        assert_eq!(AdapterKind::Jsonl.as_str(), "jsonl");
        assert_eq!(AdapterKind::Supermemory.as_str(), "supermemory");
        assert_eq!(AdapterKind::Letta.as_str(), "letta");
        assert_eq!(AdapterKind::Cognee.as_str(), "cognee");
        assert_eq!(AdapterKind::Jsonl.to_string(), "jsonl");
    }

    #[test]
    fn adapter_kind_parse_returns_known_labels() {
        assert_eq!(AdapterKind::parse("jsonl"), AdapterKind::Jsonl);
        assert_eq!(AdapterKind::parse("SUPERMEMORY"), AdapterKind::Supermemory);
        assert_eq!(AdapterKind::parse("letta"), AdapterKind::Letta);
        assert_eq!(AdapterKind::parse(" Cognee "), AdapterKind::Cognee);
        assert_eq!(AdapterKind::parse("unknown"), AdapterKind::Jsonl);
        assert_eq!(AdapterKind::parse(""), AdapterKind::Jsonl);
    }

    #[test]
    fn validate_accepts_http_and_https_base_urls() {
        validate_http_url("https://api.example.com", "TEST_URL").unwrap();
        validate_http_url("http://localhost:8080", "TEST_URL").unwrap();
    }

    #[test]
    fn validate_rejects_blank_or_non_http_urls() {
        assert!(validate_http_url("", "TEST_URL").is_err());
        assert!(validate_http_url("   ", "TEST_URL").is_err());
        assert!(validate_http_url("not-a-url", "TEST_URL").is_err());
        assert!(validate_http_url("file:///tmp/foo", "TEST_URL").is_err());
        assert!(validate_http_url("ftp://example.com", "TEST_URL").is_err());
    }

    #[test]
    fn config_build_succeeds_for_jsonl_default() {
        let config = Config::jsonl_default();
        let adapter = config.build().expect("jsonl default build");
        assert_eq!(adapter.provider_name(), "jsonl-f3-episodic");
    }

    #[test]
    fn config_validate_rejects_missing_supermemory_key() {
        let mut config = Config::jsonl_default();
        config.kind = AdapterKind::Supermemory;
        config.supermemory = Some(SupermemoryConfig {
            api_key: String::new(),
            base_url: "https://api.supermemory.ai".to_string(),
        });
        let err = config.validate().expect_err("missing key should fail");
        match err {
            SemanticMemoryError::Backend { status, body } => {
                assert_eq!(status, 401, "expected 401 backend status");
                assert!(
                    body.contains("SUPERMEMORY_API_KEY"),
                    "expected body to mention key, got {body:?}"
                );
            }
            other => panic!("expected Backend, got {other:?}"),
        }
    }

    #[test]
    fn config_validate_rejects_bad_letta_base_url() {
        let mut config = Config::jsonl_default();
        config.kind = AdapterKind::Letta;
        config.letta = Some(LettaConfig {
            api_key: "sk-letta".to_string(),
            base_url: "not-a-url".to_string(),
            default_agent_id: "agent-1".to_string(),
        });
        let err = config.validate().expect_err("bad url should fail");
        match err {
            SemanticMemoryError::InvalidResponse(message) => {
                assert!(message.contains("LETTA_BASE_URL"));
            }
            other => panic!("expected InvalidResponse, got {other:?}"),
        }
    }

    #[test]
    fn config_build_succeeds_for_supermemory_with_explicit_config() {
        let mut config = Config::jsonl_default();
        config.kind = AdapterKind::Supermemory;
        config.supermemory = Some(SupermemoryConfig {
            api_key: "sk-test".to_string(),
            base_url: "https://api.supermemory.ai".to_string(),
        });
        let adapter = config
            .build()
            .expect("supermemory adapter should build from config");
        assert_eq!(adapter.provider_name(), "supermemory");
    }

    #[test]
    fn config_build_succeeds_for_letta_with_explicit_config() {
        let mut config = Config::jsonl_default();
        config.kind = AdapterKind::Letta;
        config.letta = Some(LettaConfig {
            api_key: "sk-letta".to_string(),
            base_url: "https://api.letta.com".to_string(),
            default_agent_id: "agent-1".to_string(),
        });
        let adapter = config
            .build()
            .expect("letta adapter should build from config");
        assert_eq!(adapter.provider_name(), "letta");
    }

    #[test]
    fn config_build_succeeds_for_cognee_with_explicit_config() {
        let mut config = Config::jsonl_default();
        config.kind = AdapterKind::Cognee;
        config.cognee = Some(CogneeConfig {
            api_key: "sk-cognee".to_string(),
            base_url: "https://api.cognee.ai".to_string(),
            dataset: "ds-test".to_string(),
        });
        let adapter = config
            .build()
            .expect("cognee adapter should build from config");
        assert_eq!(adapter.provider_name(), "cognee");
    }
}
