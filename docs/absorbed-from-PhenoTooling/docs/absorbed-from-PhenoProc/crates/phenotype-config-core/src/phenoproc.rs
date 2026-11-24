//! PhenoProc configuration — consolidated defaults and structure.
//!
//! # Configuration keys
//!
//! All keys can be set via:
//! - Config file (TOML / YAML / JSON)
//! - Environment variable: `PHENOPROC_<KEY>` (uppercase, underscored)
//! - Programmatic overrides via `PhenoProcConfig { .. }`
//!
//! | Key | Type | Default | Description |
//! |-----|------|---------|-------------|
//! | `pool_default_memory_limit_mb` | u64 | `4096` | Default per-process memory cap (MB) |
//! | `pool_default_max_processes` | u32 | `100` | Default max concurrent processes |
//! | `project_default_memory_limit_mb` | u64 | `4096` | Default per-project memory cap (MB) |
//! | `project_default_max_processes` | usize | `10` | Default max processes per project |
//! | `shm_default_size` | usize | `4096` | Default shared-memory segment size (bytes) |
//! | `lock_default_ttl_secs` | u64 | `300` | Default command-lock TTL (seconds) |
//! | `uds_default_socket_dir` | String | `"/tmp"` | Default directory for UDS sockets |
//! | `router_monitor_default_url` | String | `"http://localhost:8080"` | Default router-monitor base URL |
//! | `router_monitor_api_prefix` | String | `"/api/v1"` | API prefix for router-monitor endpoints |

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// PhenoProcConfig
// ---------------------------------------------------------------------------

/// Consolidated configuration for all PhenoProc sub-crates.
///
/// Create with `PhenoProcConfig::default()` for built-in defaults, or load
/// from a file / environment via `phenotype-config-loader`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct PhenoProcConfig {
    // ---- Process pool -----------------------------------------------------
    /// Memory cap per process in MB (default: 4096).
    #[serde(default = "default_pool_memory_limit")]
    pub pool_default_memory_limit_mb: u64,

    /// Max number of concurrent processes (default: 100).
    #[serde(default = "default_pool_max_processes")]
    pub pool_default_max_processes: u32,

    // ---- Project resources ------------------------------------------------
    /// Per-project memory cap in MB (default: 4096).
    #[serde(default = "default_project_memory_limit")]
    pub project_default_memory_limit_mb: u64,

    /// Max processes per project (default: 10).
    #[serde(default = "default_project_max_processes")]
    pub project_default_max_processes: usize,

    // ---- Shared memory ----------------------------------------------------
    /// Default SHM segment size in bytes (default: 4096).
    #[serde(default = "default_shm_size")]
    pub shm_default_size: usize,

    // ---- Command lock (dedup) ---------------------------------------------
    /// Default TTL for command locks in seconds (default: 300 = 5 min).
    #[serde(default = "default_lock_ttl")]
    pub lock_default_ttl_secs: u64,

    // ---- UDS sockets ------------------------------------------------------
    /// Directory where UDS socket files are placed (default: /tmp).
    #[serde(default = "default_uds_dir")]
    pub uds_default_socket_dir: String,

    // ---- Router monitor ---------------------------------------------------
    /// Base URL of the router-monitor HTTP API (default: http://localhost:8080).
    #[serde(default = "default_router_url")]
    pub router_monitor_default_url: String,

    /// API path prefix for router-monitor endpoints (default: /api/v1).
    #[serde(default = "default_router_api_prefix")]
    pub router_monitor_api_prefix: String,
}

// ---- Default helper functions ---------------------------------------------

fn default_pool_memory_limit() -> u64 {
    4096
}
fn default_pool_max_processes() -> u32 {
    100
}
fn default_project_memory_limit() -> u64 {
    4096
}
fn default_project_max_processes() -> usize {
    10
}
fn default_shm_size() -> usize {
    4096
}
fn default_lock_ttl() -> u64 {
    300
}
fn default_uds_dir() -> String {
    "/tmp".to_string()
}
fn default_router_url() -> String {
    "http://localhost:8080".to_string()
}
fn default_router_api_prefix() -> String {
    "/api/v1".to_string()
}

impl Default for PhenoProcConfig {
    fn default() -> Self {
        Self {
            pool_default_memory_limit_mb: default_pool_memory_limit(),
            pool_default_max_processes: default_pool_max_processes(),
            project_default_memory_limit_mb: default_project_memory_limit(),
            project_default_max_processes: default_project_max_processes(),
            shm_default_size: default_shm_size(),
            lock_default_ttl_secs: default_lock_ttl(),
            uds_default_socket_dir: default_uds_dir(),
            router_monitor_default_url: default_router_url(),
            router_monitor_api_prefix: default_router_api_prefix(),
        }
    }
}

// ---- Convenience ----------------------------------------------------------

impl PhenoProcConfig {
    /// Return the lock TTL as a `std::time::Duration`.
    pub fn lock_ttl_duration(&self) -> std::time::Duration {
        std::time::Duration::from_secs(self.lock_default_ttl_secs)
    }

    /// Return `true` if the config matches the built-in defaults.
    pub fn is_default(&self) -> bool {
        self == &Self::default()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_values() {
        let cfg = PhenoProcConfig::default();
        assert_eq!(cfg.pool_default_memory_limit_mb, 4096);
        assert_eq!(cfg.pool_default_max_processes, 100);
        assert_eq!(cfg.project_default_memory_limit_mb, 4096);
        assert_eq!(cfg.project_default_max_processes, 10);
        assert_eq!(cfg.shm_default_size, 4096);
        assert_eq!(cfg.lock_default_ttl_secs, 300);
        assert_eq!(cfg.uds_default_socket_dir, "/tmp");
        assert_eq!(cfg.router_monitor_default_url, "http://localhost:8080");
        assert_eq!(cfg.router_monitor_api_prefix, "/api/v1");
    }

    #[test]
    fn test_is_default() {
        assert!(PhenoProcConfig::default().is_default());
        let mut cfg = PhenoProcConfig::default();
        cfg.pool_default_memory_limit_mb = 8192;
        assert!(!cfg.is_default());
    }

    #[test]
    fn test_lock_ttl_duration() {
        let cfg = PhenoProcConfig::default();
        assert_eq!(cfg.lock_ttl_duration(), std::time::Duration::from_secs(300));
    }

    #[test]
    fn test_serde_roundtrip_json() {
        let cfg = PhenoProcConfig::default();
        let json = serde_json::to_string(&cfg).unwrap();
        let deserialized: PhenoProcConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(cfg, deserialized);
    }

    #[test]
    fn test_serde_roundtrip_toml() {
        let cfg = PhenoProcConfig::default();
        let toml_str = toml::to_string(&cfg).unwrap();
        let deserialized: PhenoProcConfig = toml::from_str(&toml_str).unwrap();
        assert_eq!(cfg, deserialized);
    }

    #[test]
    fn test_serde_partial_override() {
        // Only specify one field; others should use defaults.
        let toml_str = r#"pool_default_memory_limit_mb = 8192"#;
        let cfg: PhenoProcConfig = toml::from_str(toml_str).unwrap();
        assert_eq!(cfg.pool_default_memory_limit_mb, 8192);
        assert_eq!(cfg.pool_default_max_processes, 100); // default
    }

    #[test]
    fn test_serde_unknown_field_rejected() {
        let toml_str = r#"unknown_field = "oops""#;
        let res: Result<PhenoProcConfig, _> = toml::from_str(toml_str);
        assert!(res.is_err(), "unknown fields should be rejected");
    }
}
