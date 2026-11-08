// SPDX-License-Identifier: MIT OR Apache-2.0
//! Daemon configuration: socket/pid paths, heartbeat timeouts, log level,
//! max line size, idle timeout, stop timeout.
//!
//! # Sources (highest to lowest priority)
//!
//! 1. CLI arguments (passed directly to constructors)
//! 2. Environment variables (`TEAMCOMM_*`)
//! 3. Config file (TOML — `TEAMCOMM_CONFIG` env var, then
//!    `./teamcomm.toml`, then `~/.config/teamcomm/teamcomm.toml`,
//!    then `/etc/teamcomm/teamcomm.toml`)
//! 4. Built-in defaults
//!
//! # Environment variables
//!
//! | Variable                          | Maps to field            |
//! |-----------------------------------|--------------------------|
//! | `TEAMCOMM_SOCKET_PATH`            | `socket_path`            |
//! | `TEAMCOMM_PID_FILE_PATH`          | `pid_file_path`          |
//! | `TEAMCOMM_HEARTBEAT_TIMEOUT_SEC`  | `heartbeat_timeout_sec`  |
//! | `TEAMCOMM_LOG_LEVEL`              | `log_level`              |
//! | `TEAMCOMM_MAX_LINE_BYTES`         | `max_line_bytes`         |
//! | `TEAMCOMM_IDLE_TIMEOUT_SEC`       | `idle_timeout_sec`       |
//! | `TEAMCOMM_STOP_TIMEOUT_SEC`       | `stop_timeout_sec`       |
//! | `TEAMCOMM_CONFIG`                 | config file path         |

use std::env;
use std::path::{Path, PathBuf};

use serde::Deserialize;

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

/// Static configuration for a running daemon instance.
///
/// All paths are resolved at construction time (via [`DaemonConfig::load`],
/// [`DaemonConfig::from_args`], or [`DaemonConfig::default_paths`]); the
/// listener does no further path manipulation at runtime.
#[derive(Debug, Clone, Deserialize)]
#[serde(default)]
pub struct DaemonConfig {
    /// Path of the Unix-domain socket the daemon listens on.
    pub socket_path: PathBuf,
    /// Path of the file the daemon writes its PID to on startup.
    pub pid_file_path: PathBuf,
    /// A session is considered lost after this many seconds without a
    /// heartbeat. M0 does not actually sweep lost sessions; M1 will.
    /// Default: 90 (3 missed 30-second heartbeats).
    pub heartbeat_timeout_sec: u64,
    /// Tracing/log filter string (e.g. `"info"`, `"teamcomm_daemon=debug"`).
    /// Default: `"info"`.
    pub log_level: String,
    /// Maximum bytes a single JSON-RPC request line may contain. Lines
    /// exceeding this are rejected with a parse error.
    /// Default: 1 048 576 (1 MiB).
    pub max_line_bytes: usize,
    /// Seconds of inactivity after which an idle connection is closed.
    /// Default: 300 (5 minutes).
    pub idle_timeout_sec: u64,
    /// Seconds the `stop` subcommand waits for the daemon process to exit
    /// before removing the pid file unilaterally.
    /// Default: 3.
    pub stop_timeout_sec: u64,
}

impl Default for DaemonConfig {
    fn default() -> Self {
        let (sock, pid) = default_paths();
        Self {
            socket_path: sock,
            pid_file_path: pid,
            heartbeat_timeout_sec: 90,
            log_level: "info".to_string(),
            max_line_bytes: 1024 * 1024, // 1 MiB
            idle_timeout_sec: 5 * 60,    // 5 minutes
            stop_timeout_sec: 3,
        }
    }
}

impl DaemonConfig {
    // ---- Constructors ----

    /// Load configuration using the layered priority scheme:
    ///
    /// 1. Built-in defaults
    /// 2. Config file (if found; see [`find_config_file`])
    /// 3. Environment variables (`TEAMCOMM_*`)
    ///
    /// CLI-provided overrides can be applied afterward via
    /// [`DaemonConfig::apply_cli_overrides`].
    pub fn load() -> Self {
        let mut cfg = Self::default();

        // Layer 2: config file
        if let Some(config_path) = find_config_file() {
            if let Ok(contents) = std::fs::read_to_string(&config_path) {
                if let Ok(file_cfg) = toml::from_str::<DaemonConfig>(&contents) {
                    cfg = cfg.merge(file_cfg);
                }
                // Silently ignore unreadable / malformed files so the
                // daemon can still start with env / CLI overrides.
            }
        }

        // Layer 3: environment variables
        cfg.apply_env_overrides();

        cfg
    }

    /// Build a [`DaemonConfig`] from explicit optional paths, falling back
    /// to [`default_paths`] for any field that is `None`.
    ///
    /// Timeout and log-level fields retain their default values (use
    /// [`with_overrides`](Self::with_overrides) to customise those, or
    /// [`load`](Self::load) for full env / file support).
    pub fn from_args(socket: Option<PathBuf>, pid_file: Option<PathBuf>) -> Self {
        let (def_sock, def_pid) = default_paths();
        Self {
            socket_path: socket.unwrap_or(def_sock),
            pid_file_path: pid_file.unwrap_or(def_pid),
            ..Self::default()
        }
    }

    /// Build a [`DaemonConfig`] with the default socket/pid paths and
    /// custom timeouts / log level.
    pub fn with_overrides(
        socket: Option<PathBuf>,
        pid_file: Option<PathBuf>,
        heartbeat_timeout_sec: u64,
        log_level: String,
    ) -> Self {
        let mut cfg = Self::from_args(socket, pid_file);
        cfg.heartbeat_timeout_sec = heartbeat_timeout_sec;
        cfg.log_level = log_level;
        cfg
    }

    // ---- Public helpers ----

    /// Override fields from CLI argument values (only `Some` fields are
    /// applied).
    pub fn apply_cli_overrides(
        &mut self,
        socket: Option<PathBuf>,
        pid_file: Option<PathBuf>,
    ) -> &mut Self {
        if let Some(s) = socket {
            self.socket_path = s;
        }
        if let Some(p) = pid_file {
            self.pid_file_path = p;
        }
        self
    }

    /// Helper: derive a parent directory from the socket path. Used by
    /// the listener when it needs to `mkdir -p` the runtime dir.
    pub fn socket_parent(&self) -> &Path {
        self.socket_path
            .parent()
            .unwrap_or_else(|| Path::new("/tmp"))
    }

    // ---- Private helpers ----

    /// Merge non-default fields from `other` into `self` (a field from
    /// `other` is applied only if it differs from *its own* default,
    /// simulating "config file fields override defaults").
    fn merge(self, other: Self) -> Self {
        let def = Self::default();
        Self {
            socket_path: if other.socket_path != def.socket_path {
                other.socket_path
            } else {
                self.socket_path
            },
            pid_file_path: if other.pid_file_path != def.pid_file_path {
                other.pid_file_path
            } else {
                self.pid_file_path
            },
            heartbeat_timeout_sec: if other.heartbeat_timeout_sec != def.heartbeat_timeout_sec {
                other.heartbeat_timeout_sec
            } else {
                self.heartbeat_timeout_sec
            },
            log_level: if other.log_level != def.log_level {
                other.log_level
            } else {
                self.log_level
            },
            max_line_bytes: if other.max_line_bytes != def.max_line_bytes {
                other.max_line_bytes
            } else {
                self.max_line_bytes
            },
            idle_timeout_sec: if other.idle_timeout_sec != def.idle_timeout_sec {
                other.idle_timeout_sec
            } else {
                self.idle_timeout_sec
            },
            stop_timeout_sec: if other.stop_timeout_sec != def.stop_timeout_sec {
                other.stop_timeout_sec
            } else {
                self.stop_timeout_sec
            },
        }
    }

    /// Override fields from `TEAMCOMM_*` environment variables.
    fn apply_env_overrides(&mut self) {
        env_var_opt("TEAMCOMM_SOCKET_PATH").map(|v| self.socket_path = PathBuf::from(v));
        env_var_opt("TEAMCOMM_PID_FILE_PATH").map(|v| self.pid_file_path = PathBuf::from(v));
        env_var_opt("TEAMCOMM_HEARTBEAT_TIMEOUT_SEC")
            .and_then(parse_u64)
            .map(|v| self.heartbeat_timeout_sec = v);
        env_var_opt("TEAMCOMM_LOG_LEVEL").map(|v| self.log_level = v);
        env_var_opt("TEAMCOMM_MAX_LINE_BYTES")
            .and_then(parse_usize)
            .map(|v| self.max_line_bytes = v);
        env_var_opt("TEAMCOMM_IDLE_TIMEOUT_SEC")
            .and_then(parse_u64)
            .map(|v| self.idle_timeout_sec = v);
        env_var_opt("TEAMCOMM_STOP_TIMEOUT_SEC")
            .and_then(parse_u64)
            .map(|v| self.stop_timeout_sec = v);
    }
}

// ---------------------------------------------------------------------------
// Default paths
// ---------------------------------------------------------------------------

/// Default socket and pid file paths.
///
/// Uses [`dirs::runtime_dir`] (which maps to `$XDG_RUNTIME_DIR` on Linux
/// and `$TMPDIR` on macOS) and falls back to `/tmp` when no runtime dir
/// is available.
pub fn default_paths() -> (PathBuf, PathBuf) {
    let runtime = dirs::runtime_dir().unwrap_or_else(|| PathBuf::from("/tmp"));
    (
        runtime.join("teamcomm").join("daemon.sock"),
        runtime.join("teamcomm").join("daemon.pid"),
    )
}

// ---------------------------------------------------------------------------
// Config file discovery
// ---------------------------------------------------------------------------

/// Search for a teamcomm config file in well-known locations.
///
/// Priority:
/// 1. `$TEAMCOMM_CONFIG` (explicit path)
/// 2. `./teamcomm.toml`
/// 3. `$XDG_CONFIG_HOME/teamcomm/teamcomm.toml` (or `~/.config/teamcomm/teamcomm.toml`)
/// 4. `/etc/teamcomm/teamcomm.toml`
pub fn find_config_file() -> Option<PathBuf> {
    // 1. Explicit env var
    if let Some(path) = env_var_opt("TEAMCOMM_CONFIG") {
        let p = PathBuf::from(path);
        if p.is_file() {
            return Some(p);
        }
    }

    // 2. CWD
    let cwd = PathBuf::from("./teamcomm.toml");
    if cwd.is_file() {
        return Some(cwd);
    }

    // 3. XDG / home config
    if let Some(config_dir) = dirs::config_dir() {
        let xdg_path = config_dir.join("teamcomm").join("teamcomm.toml");
        if xdg_path.is_file() {
            return Some(xdg_path);
        }
    }

    // 4. Global /etc
    let etc_path = PathBuf::from("/etc/teamcomm/teamcomm.toml");
    if etc_path.is_file() {
        return Some(etc_path);
    }

    None
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Read an environment variable, returning `None` if unset or empty.
fn env_var_opt(key: &str) -> Option<String> {
    let val = env::var(key).ok()?;
    if val.is_empty() {
        None
    } else {
        Some(val)
    }
}

fn parse_u64(s: String) -> Option<u64> {
    s.parse::<u64>().ok()
}

fn parse_usize(s: String) -> Option<usize> {
    s.parse::<usize>().ok()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn from_args_uses_defaults_when_none() {
        let cfg = DaemonConfig::from_args(None, None);
        let (def_sock, def_pid) = default_paths();
        assert_eq!(cfg.socket_path, def_sock);
        assert_eq!(cfg.pid_file_path, def_pid);
        assert_eq!(cfg.heartbeat_timeout_sec, 90);
        assert_eq!(cfg.log_level, "info");
        assert_eq!(cfg.max_line_bytes, 1024 * 1024);
        assert_eq!(cfg.idle_timeout_sec, 300);
        assert_eq!(cfg.stop_timeout_sec, 3);
    }

    #[test]
    fn from_args_respects_overrides() {
        let sock = PathBuf::from("/tmp/custom.sock");
        let pid = PathBuf::from("/tmp/custom.pid");
        let cfg = DaemonConfig::from_args(Some(sock.clone()), Some(pid.clone()));
        assert_eq!(cfg.socket_path, sock);
        assert_eq!(cfg.pid_file_path, pid);
    }

    #[test]
    fn with_overrides_replaces_timeouts_and_log_level() {
        let cfg = DaemonConfig::with_overrides(None, None, 30, "debug".into());
        assert_eq!(cfg.heartbeat_timeout_sec, 30);
        assert_eq!(cfg.log_level, "debug");
    }

    #[test]
    fn socket_parent_strips_filename() {
        let cfg = DaemonConfig::from_args(
            Some(PathBuf::from("/a/b/c.sock")),
            Some(PathBuf::from("/a/b/c.pid")),
        );
        assert_eq!(cfg.socket_parent(), Path::new("/a/b"));
    }

    #[test]
    fn default_paths_contain_teamcomm_dir() {
        let (sock, pid) = default_paths();
        assert!(sock.ends_with("daemon.sock"), "got {sock:?}");
        assert!(pid.ends_with("daemon.pid"), "got {pid:?}");
        assert_eq!(sock.parent(), pid.parent());
    }

    #[test]
    fn defaults_all_fields() {
        let cfg = DaemonConfig::default();
        assert_eq!(cfg.heartbeat_timeout_sec, 90);
        assert_eq!(cfg.log_level, "info");
        assert_eq!(cfg.max_line_bytes, 1024 * 1024);
        assert_eq!(cfg.idle_timeout_sec, 300);
        assert_eq!(cfg.stop_timeout_sec, 3);
        assert!(
            cfg.socket_path.to_string_lossy().ends_with("daemon.sock"),
            "socket_path ends with daemon.sock"
        );
        assert!(
            cfg.pid_file_path.to_string_lossy().ends_with("daemon.pid"),
            "pid_file_path ends with daemon.pid"
        );
    }

    #[test]
    fn deserialize_from_toml_overrides_partial() {
        let toml_str = r#"
heartbeat_timeout_sec = 45
max_line_bytes = 65536
idle_timeout_sec = 600
"#;
        let cfg: DaemonConfig = toml::from_str(toml_str).unwrap();
        // These should match the TOML values.
        assert_eq!(cfg.heartbeat_timeout_sec, 45);
        assert_eq!(cfg.max_line_bytes, 65536);
        assert_eq!(cfg.idle_timeout_sec, 600);
        // These should fall through to Default.
        assert_eq!(cfg.log_level, "info");
        assert_eq!(cfg.stop_timeout_sec, 3);
    }

    #[test]
    fn deserialize_from_toml_full() {
        let toml_str = r#"
socket_path = "/var/run/teamcomm/custom.sock"
pid_file_path = "/var/run/teamcomm/custom.pid"
heartbeat_timeout_sec = 120
log_level = "teamcomm_daemon=debug"
max_line_bytes = 2097152
idle_timeout_sec = 1800
stop_timeout_sec = 10
"#;
        let cfg: DaemonConfig = toml::from_str(toml_str).unwrap();
        assert_eq!(
            cfg.socket_path,
            PathBuf::from("/var/run/teamcomm/custom.sock")
        );
        assert_eq!(
            cfg.pid_file_path,
            PathBuf::from("/var/run/teamcomm/custom.pid")
        );
        assert_eq!(cfg.heartbeat_timeout_sec, 120);
        assert_eq!(cfg.log_level, "teamcomm_daemon=debug");
        assert_eq!(cfg.max_line_bytes, 2097152);
        assert_eq!(cfg.idle_timeout_sec, 1800);
        assert_eq!(cfg.stop_timeout_sec, 10);
    }

    #[test]
    fn find_config_file_returns_none_when_no_file() {
        // Should return None when no config file exists in any location
        let prev = env_var_opt("TEAMCOMM_CONFIG");
        // We just verify the function doesn't panic.
        let _ = find_config_file();
        // If TEAMCOMM_CONFIG was set, restore it.
        if let Some(v) = prev {
            unsafe {
                env::set_var("TEAMCOMM_CONFIG", v);
            }
        }
    }

    #[test]
    fn env_var_opt_returns_none_for_empty() {
        unsafe {
            env::set_var("_TEAMCOMM_TEST_EMPTY", "");
        }
        assert!(env_var_opt("_TEAMCOMM_TEST_EMPTY").is_none());
        unsafe {
            env::remove_var("_TEAMCOMM_TEST_EMPTY");
        }
    }

    #[test]
    fn env_override_mutates_config() {
        unsafe {
            env::set_var("TEAMCOMM_HEARTBEAT_TIMEOUT_SEC", "77");
            env::set_var("TEAMCOMM_LOG_LEVEL", "trace");
            env::set_var("TEAMCOMM_MAX_LINE_BYTES", "512");
            env::set_var("TEAMCOMM_STOP_TIMEOUT_SEC", "15");
        }

        let cfg = DaemonConfig::load();

        unsafe {
            env::remove_var("TEAMCOMM_HEARTBEAT_TIMEOUT_SEC");
            env::remove_var("TEAMCOMM_LOG_LEVEL");
            env::remove_var("TEAMCOMM_MAX_LINE_BYTES");
            env::remove_var("TEAMCOMM_STOP_TIMEOUT_SEC");
        }

        assert_eq!(cfg.heartbeat_timeout_sec, 77);
        assert_eq!(cfg.log_level, "trace");
        assert_eq!(cfg.max_line_bytes, 512);
        assert_eq!(cfg.stop_timeout_sec, 15);
    }

    #[test]
    fn apply_cli_overrides_works() {
        let mut cfg = DaemonConfig::default();
        let sock = PathBuf::from("/cli/custom.sock");
        let pid = PathBuf::from("/cli/custom.pid");
        cfg.apply_cli_overrides(Some(sock.clone()), Some(pid.clone()));
        assert_eq!(cfg.socket_path, sock);
        assert_eq!(cfg.pid_file_path, pid);
        // Unchanged fields should remain default.
        assert_eq!(cfg.heartbeat_timeout_sec, 90);
    }

    #[test]
    fn apply_cli_overrides_none_does_not_change() {
        let mut cfg = DaemonConfig::default();
        let original_sock = cfg.socket_path.clone();
        let original_pid = cfg.pid_file_path.clone();
        cfg.apply_cli_overrides(None, None);
        assert_eq!(cfg.socket_path, original_sock);
        assert_eq!(cfg.pid_file_path, original_pid);
    }

    #[test]
    fn merge_updates_only_different_fields() {
        let def = DaemonConfig::default();
        let custom = DaemonConfig {
            heartbeat_timeout_sec: 42,
            ..def.clone()
        };
        let merged = def.clone().merge(custom);
        assert_eq!(merged.heartbeat_timeout_sec, 42);
        assert_eq!(merged.log_level, "info");
        assert_eq!(merged.socket_path, def.socket_path);
    }

    #[test]
    fn env_var_opt_basics() {
        unsafe {
            env::set_var("_TEAMCOMM_TEST_VAL", "hello");
        }
        assert_eq!(env_var_opt("_TEAMCOMM_TEST_VAL").as_deref(), Some("hello"));
        unsafe {
            env::remove_var("_TEAMCOMM_TEST_VAL");
        }
        assert!(env_var_opt("_TEAMCOMM_TEST_VAL").is_none());
    }
}
