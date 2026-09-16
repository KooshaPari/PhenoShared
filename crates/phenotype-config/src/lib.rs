//! # phenotype-config
//!
//! Layered configuration for Phenotype tooling.
//!
//! Loads config from (in order of precedence):
//! 1. Environment variables (prefix `PHENOTYPE_`)
//! 2. Config file (`phenotype.toml`, `phenotype.json`, `phenotype.yaml`)
//! 3. Built-in defaults
//!
//! ## Environment variable mapping
//!
//! Nested keys use `__` as separator. For example:
//! - `PHENOTYPE_SERVICE_HOST` → `service.host`
//! - `PHENOTYPE_SERVICE_PORT` → `service.port`
//! - `PHENOTYPE_PATHS__SBOM_OUTPUT` → `paths.sbom_output`

use figment::{
    providers::{Env, Format, Json, Serialized, Toml, Yaml},
    Figment,
};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use uncased::Uncased;

// ──── Top-level config ────────────────────────────────────────────────────────

/// All configurable Phenotype values.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct PhenotypeConfig {
    pub environment: Option<String>,

    /// Service registry defaults
    pub service: ServiceConfig,

    /// File system paths used by Phenotype tools
    pub paths: PathsConfig,

    /// Webhook / notification targets
    pub webhooks: WebhooksConfig,

    /// Resilience / timeout defaults
    pub resilience: ResilienceConfig,

    /// Quality gate tool paths
    pub quality_gate: QualityGateConfig,

    /// API keys loaded from environment or file
    pub api_keys: ApiKeysConfig,
}

// ──── Sub-configs ─────────────────────────────────────────────────────────────

/// Service registry defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceConfig {
    /// Default host for service registrations (default: 127.0.0.1)
    pub host: String,
    /// Default port for service registrations (default: 8080)
    pub port: u16,
}

/// Filesystem paths used by Phenotype tools.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathsConfig {
    /// Home directory override (default: $HOME or `.`)
    pub home_dir: Option<PathBuf>,
    /// Claude config directory name (default: `.claude`)
    pub claude_dir_name: String,
    /// Usage snapshot output path relative to claude_dir (default: `usage.json`)
    pub usage_output: String,
    /// Active agents tracking file relative to claude_dir (default: `active-agents.json`)
    pub active_agents: String,
    /// Documentation site root directory (default: `docs-site`)
    pub docs_root: PathBuf,
    /// SBOM output path (default: `docs/security/sbom.json`)
    pub sbom_output: PathBuf,
}

/// Webhook / notification configuration.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct WebhooksConfig {
    /// Discord webhook URL for release announcements
    pub discord_webhook_url: String,
}

/// Resilience / timeout defaults.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResilienceConfig {
    /// Circuit breaker recovery timeout in seconds (default: 60)
    pub circuit_breaker_recovery_secs: u64,
    /// Rate limiter default interval in milliseconds (default: 1000)
    pub rate_limiter_default_interval_ms: u64,
    /// Bulkhead default sleep in milliseconds (default: 50)
    pub bulkhead_default_sleep_ms: u64,
}

/// Quality gate tool paths (repo-relative).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityGateConfig {
    /// Path to deny.toml (default: `deny.toml`)
    pub deny_toml: PathBuf,
    /// Path to fr-coverage binary (default: `tooling/fr-coverage/target/release/fr-coverage`)
    pub fr_coverage_bin: PathBuf,
    /// Path to doc-link-check binary (default: `tooling/doc-link-check/target/release/doc-link-check`)
    pub doc_link_check_bin: PathBuf,
    /// Path to bun.lockb marker (default: `apps/builder/bun.lockb`)
    pub bun_lockb: PathBuf,
}

/// API keys sourced from environment or config file.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ApiKeysConfig {
    /// Anthropic admin API key
    pub anthropic_admin_key: Option<String>,
}

// ──── Defaults matching existing hardcoded values ─────────────────────────────

impl Default for ServiceConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".into(),
            port: 8080,
        }
    }
}

impl Default for PathsConfig {
    fn default() -> Self {
        Self {
            home_dir: None,
            claude_dir_name: ".claude".into(),
            usage_output: "usage.json".into(),
            active_agents: "active-agents.json".into(),
            docs_root: PathBuf::from("docs-site"),
            sbom_output: PathBuf::from("docs/security/sbom.json"),
        }
    }
}

impl Default for ResilienceConfig {
    fn default() -> Self {
        Self {
            circuit_breaker_recovery_secs: 60,
            rate_limiter_default_interval_ms: 1000,
            bulkhead_default_sleep_ms: 50,
        }
    }
}

impl Default for QualityGateConfig {
    fn default() -> Self {
        Self {
            deny_toml: PathBuf::from("deny.toml"),
            fr_coverage_bin: PathBuf::from("tooling/fr-coverage/target/release/fr-coverage"),
            doc_link_check_bin: PathBuf::from(
                "tooling/doc-link-check/target/release/doc-link-check",
            ),
            bun_lockb: PathBuf::from("apps/builder/bun.lockb"),
        }
    }
}

// ──── Loading ─────────────────────────────────────────────────────────────────

impl PhenotypeConfig {
    /// Load config using the default layered provider chain:
    ///
    /// 1. Built-in defaults (via `Default`)
    /// 2. Config file: `phenotype.toml` (or `.json` / `.yaml`) in cwd
    /// 3. Environment variables with `PHENOTYPE_` prefix
    ///
    /// Environment variables use `__` as nested separator:
    /// - `PHENOTYPE_SERVICE_HOST` → `service.host`
    /// - `PHENOTYPE_PATHS__DOCS_ROOT` → `paths.docs_root`
    /// - `PHENOTYPE_WEBHOOKS__DISCORD_WEBHOOK_URL` → `webhooks.discord_webhook_url`
    pub fn load() -> Result<Self, ConfigError> {
        Self::load_from(None)
    }

    /// Load config, optionally specifying a config file path.
    ///
    /// Providers, in order of increasing precedence:
    /// 1. Built-in defaults
    /// 2. Config file (TOML, JSON, or YAML)
    /// 3. `PHENOTYPE_*` environment variables
    pub fn load_from(config_path: Option<&std::path::Path>) -> Result<Self, ConfigError> {
        let mut figment = Figment::from(Serialized::defaults(PhenotypeConfig::default()));

        // Config file (if provided or if default files exist)
        if let Some(path) = config_path {
            if path.exists() {
                let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
                figment = match ext {
                    "toml" => figment.merge(Toml::file(path)),
                    "json" => figment.merge(Json::file(path)),
                    "yaml" | "yml" => figment.merge(Yaml::file(path)),
                    _ => {
                        return Err(ConfigError::UnsupportedFormat(ext.into()));
                    }
                };
            }
        } else {
            // Try default config files
            for candidate in &[
                "phenotype.toml",
                "phenotype.json",
                "phenotype.yaml",
                "phenotype.yml",
            ] {
                let p = std::path::Path::new(candidate);
                if p.exists() {
                    let ext = p.extension().and_then(|e| e.to_str()).unwrap_or("");
                    figment = match ext {
                        "toml" => figment.merge(Toml::file(p)),
                        "json" => figment.merge(Json::file(p)),
                        "yaml" | "yml" => figment.merge(Yaml::file(p)),
                        _ => continue,
                    };
                    break;
                }
            }
        }

        // Environment variables (PHENOTYPE_ prefix, __ as nested separator).
        //
        // Two-tier mapping:
        // 1. `PHENOTYPE_FOO__BAR` (double underscore) → `foo.bar` via `.split("__")`
        // 2. `PHENOTYPE_FOO_BAR` (single underscore)   → `foo.bar` via `.map(...)`
        //
        // Single-underscore keys get rewritten so the simple `PHENOTYPE_SERVICE_HOST`
        // form maps to `service.host` (matching the struct field).
        figment = figment.merge(Env::prefixed("PHENOTYPE_").split("__").map(|k| {
            let raw = k.as_str();
            let lowered = raw.to_ascii_lowercase();
            // Only convert the FIRST `_` to `.` when the key isn't
            // already dotted (i.e., it wasn't produced by `.split("__")`).
            // Otherwise, a key like `circuit_breaker_recovery_secs` from
            // `PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS` would
            // get corrupted to `circuit.breaker_recovery_secs`.
            let dotted = if lowered.contains('.') {
                lowered
            } else {
                lowered.replacen('_', ".", 1)
            };
            Uncased::new(dotted)
        }));

        let config: PhenotypeConfig = figment
            .extract()
            .map_err(|e| ConfigError::ExtractionFailed(e.to_string()))?;

        // Override home_dir from $HOME if not set
        let config = Self {
            paths: PathsConfig {
                home_dir: config.paths.home_dir.or_else(|| {
                    std::env::var("HOME")
                        .ok()
                        .map(PathBuf::from)
                        .or_else(|| std::env::var("USERPROFILE").ok().map(PathBuf::from))
                }),
                ..config.paths
            },
            ..config
        };

        Ok(config)
    }

    // ──── Convenience accessors ──────────────────────────────────────────────

    /// Resolve the home directory.
    pub fn home_dir(&self) -> &std::path::Path {
        self.paths
            .home_dir
            .as_deref()
            .unwrap_or_else(|| std::path::Path::new("."))
    }

    /// Resolve the Claude config directory path.
    pub fn claude_dir(&self) -> PathBuf {
        self.home_dir().join(&self.paths.claude_dir_name)
    }

    /// Full path to usage output file.
    pub fn usage_output_path(&self) -> PathBuf {
        self.claude_dir().join(&self.paths.usage_output)
    }

    /// Full path to active agents file.
    pub fn active_agents_path(&self) -> PathBuf {
        self.claude_dir().join(&self.paths.active_agents)
    }
}

// ──── Error type ──────────────────────────────────────────────────────────────

/// Errors that can occur during config loading.
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    /// The config file format is not supported.
    #[error("unsupported config file format: {0}")]
    UnsupportedFormat(String),

    /// Failed to extract config from providers.
    #[error("failed to extract config: {0}")]
    ExtractionFailed(String),
}

// ──── Tests ───────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    // Tests below mutate process-global env vars (`PHENOTYPE_*`, `HOME`).
    // Cargo runs tests in parallel by default, so we serialize them through
    // this mutex to keep the assertions deterministic.
    static ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    #[test]
    fn test_default_config_loads() {
        let _g = ENV_LOCK.lock().unwrap();
        // Make sure no PHENOTYPE_* leftovers from other tests influence the defaults.
        for var in [
            "PHENOTYPE_SERVICE_HOST",
            "PHENOTYPE_SERVICE_PORT",
            "PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS",
            "PHENOTYPE_RESILIENCE__BULKHEAD_DEFAULT_SLEEP_MS",
        ] {
            std::env::remove_var(var);
        }
        // Load from just defaults (no config file, no env overrides)
        let config = PhenotypeConfig::load().expect("default config should load");
        assert_eq!(config.service.host, "127.0.0.1");
        assert_eq!(config.service.port, 8080);
        assert_eq!(config.paths.docs_root, PathBuf::from("docs-site"));
        assert_eq!(
            config.paths.sbom_output,
            PathBuf::from("docs/security/sbom.json")
        );
        assert_eq!(config.resilience.circuit_breaker_recovery_secs, 60);
        assert_eq!(config.resilience.bulkhead_default_sleep_ms, 50);
    }

    #[test]
    fn test_config_from_toml_file() {
        let _g = ENV_LOCK.lock().unwrap();
        for var in [
            "PHENOTYPE_SERVICE_HOST",
            "PHENOTYPE_SERVICE_PORT",
            "PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS",
            "PHENOTYPE_RESILIENCE__BULKHEAD_DEFAULT_SLEEP_MS",
        ] {
            std::env::remove_var(var);
        }
        let dir = std::env::temp_dir();
        let config_path = dir.join("test_phenotype_config.toml");
        let toml_content = r#"
[service]
host = "0.0.0.0"
port = 9090

[paths]
docs_root = "custom-docs"
sbom_output = "custom/sbom.json"

[resilience]
circuit_breaker_recovery_secs = 120

[webhooks]
discord_webhook_url = "https://discord.com/api/webhooks/test"
"#;
        fs::write(&config_path, toml_content).expect("should write test config");

        let config = PhenotypeConfig::load_from(Some(&config_path)).expect("should load from file");
        assert_eq!(config.service.host, "0.0.0.0");
        assert_eq!(config.service.port, 9090);
        assert_eq!(config.paths.docs_root, PathBuf::from("custom-docs"));
        assert_eq!(config.paths.sbom_output, PathBuf::from("custom/sbom.json"));
        assert_eq!(config.resilience.circuit_breaker_recovery_secs, 120);
        assert_eq!(
            config.webhooks.discord_webhook_url,
            "https://discord.com/api/webhooks/test"
        );

        // Cleanup
        fs::remove_file(&config_path).ok();
    }

    #[test]
    fn test_convenience_paths() {
        let _g = ENV_LOCK.lock().unwrap();
        for var in [
            "PHENOTYPE_SERVICE_HOST",
            "PHENOTYPE_SERVICE_PORT",
            "PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS",
            "PHENOTYPE_RESILIENCE__BULKHEAD_DEFAULT_SLEEP_MS",
        ] {
            std::env::remove_var(var);
        }
        // Temporarily set HOME for testing
        let original_home = std::env::var("HOME").ok();
        std::env::set_var("HOME", "/tmp/test-user");

        let config = PhenotypeConfig::load().expect("should load defaults");
        assert_eq!(config.claude_dir(), PathBuf::from("/tmp/test-user/.claude"));
        assert_eq!(
            config.usage_output_path(),
            PathBuf::from("/tmp/test-user/.claude/usage.json")
        );
        assert_eq!(
            config.active_agents_path(),
            PathBuf::from("/tmp/test-user/.claude/active-agents.json")
        );

        // Restore HOME
        if let Some(home) = original_home {
            std::env::set_var("HOME", home);
        } else {
            std::env::remove_var("HOME");
        }
    }

    #[test]
    fn test_env_overrides_service_host() {
        let _g = ENV_LOCK.lock().unwrap();
        for var in [
            "PHENOTYPE_SERVICE_PORT",
            "PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS",
            "PHENOTYPE_RESILIENCE__BULKHEAD_DEFAULT_SLEEP_MS",
        ] {
            std::env::remove_var(var);
        }
        // Temporarily set env var and verify it overrides defaults
        std::env::set_var("PHENOTYPE_SERVICE_HOST", "10.0.0.1");
        let config = PhenotypeConfig::load().expect("should load with env override");
        assert_eq!(config.service.host, "10.0.0.1");
        // Other fields should still be defaults
        assert_eq!(config.service.port, 8080);
        std::env::remove_var("PHENOTYPE_SERVICE_HOST");
    }

    #[test]
    fn test_nested_env_overrides() {
        let _g = ENV_LOCK.lock().unwrap();
        for var in ["PHENOTYPE_SERVICE_HOST"] {
            std::env::remove_var(var);
        }
        std::env::set_var("PHENOTYPE_SERVICE_PORT", "3000");
        std::env::set_var("PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS", "300");
        let config = PhenotypeConfig::load().expect("should handle nested env");
        assert_eq!(config.service.port, 3000);
        assert_eq!(config.resilience.circuit_breaker_recovery_secs, 300);
        std::env::remove_var("PHENOTYPE_SERVICE_PORT");
        std::env::remove_var("PHENOTYPE_RESILIENCE__CIRCUIT_BREAKER_RECOVERY_SECS");
    }
}
