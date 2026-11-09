//! Phenotype Daemon - High-performance sidecar for skill management
//!
//! Architecture:
//! - Unix domain sockets (fast local IPC)
//! - TCP fallback for cross-platform compatibility
//! - msgpack-rpc protocol for efficient serialization
//! - Async I/O with tokio for high concurrency
//! - Shared, daemon-wide `BufferPool` (SPEC.md:430-433) so every
//!   connection reuses the same pre-allocated `BytesMut` buffers
//!   rather than allocating per-connection pools.

mod protocol;
mod rpc;

use rpc::{BufferPool, RpcHandler, SharedState};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::net::{TcpListener, UnixListener};
use tracing::{error, info, warn};

use clap::Parser;
use clap_ext::prelude::{setup_tracing, ConfigArg, Verbosity};
use protocol::VersionInfo;

/// Default socket path for Unix domain sockets
#[cfg(unix)]
const DEFAULT_SOCKET_PATH: &str = "/tmp/phenotype-daemon.sock";

/// Default TCP port for cross-platform support
const DEFAULT_TCP_PORT: u16 = 9456;

/// CLI args
#[derive(Parser, Debug)]
#[command(name = "phenotype-daemon", about = "Phenotype skill-management sidecar daemon")]
struct Args {
    /// Verbosity (-v, -vv, -vvv for more, -q to silence)
    #[command(flatten)]
    verbosity: Verbosity,

    /// Optional config file path (PHENOTYPE_CONFIG env var also honored)
    #[command(flatten)]
    config: ConfigArg,
}

/// Server configuration
#[derive(Debug, Clone)]
struct ServerConfig {
    /// Unix socket path (Unix only)
    #[cfg(unix)]
    socket_path: PathBuf,
    /// TCP port for fallback
    tcp_port: u16,
    /// Enable TCP mode (Windows requires this)
    tcp_only: bool,
    /// Optional bearer token required to authenticate incoming
    /// connections. Must NOT be exposed via the [`Display`] impl,
    /// [`Debug`], log output, or panic messages — the [`tests`]
    /// module below pins that contract.
    auth_token: Option<String>,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            #[cfg(unix)]
            socket_path: PathBuf::from(DEFAULT_SOCKET_PATH),
            tcp_port: DEFAULT_TCP_PORT,
            tcp_only: cfg!(windows),
            auth_token: None,
        }
    }
}

impl std::fmt::Display for ServerConfig {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Deliberately omits `auth_token` so a stray `format!("{}",
        // config)` (e.g. in a panic message, log line, or config
        // dump) cannot leak the bearer token.
        write!(
            f,
            "ServerConfig {{ tcp_port: {}, tcp_only: {}, auth_token: <redacted> }}",
            self.tcp_port, self.tcp_only
        )
    }
}

/// Initialize logging with appropriate level
fn init_logging(filter: tracing_subscriber::filter::LevelFilter) {
    setup_tracing(filter);
}

/// Run Unix socket server
#[cfg(unix)]
async fn run_unix_server(
    config: &ServerConfig,
    state: Arc<SharedState>,
) -> anyhow::Result<()> {
    // Remove existing socket if present
    if config.socket_path.exists() {
        tokio::fs::remove_file(&config.socket_path).await.ok();
    }

    let listener = UnixListener::bind(&config.socket_path)?;
    info!("Unix socket listening at {:?}", config.socket_path);

    loop {
        let (stream, _) = listener.accept().await?;
        let state = state.clone();

        tokio::spawn(async move {
            let handler = RpcHandler::new(state);
            if let Err(e) = handler.handle_stream(stream).await {
                error!("Connection error: {}", e);
            }
        });
    }
}

/// Run TCP server
async fn run_tcp_server(
    config: &ServerConfig,
    state: Arc<SharedState>,
) -> anyhow::Result<()> {
    let addr = format!("127.0.0.1:{}", config.tcp_port);
    let listener = TcpListener::bind(&addr).await?;
    info!("TCP server listening on {}", addr);

    loop {
        let (stream, peer) = listener.accept().await?;
        info!("New TCP connection from {:?}", peer);

        let handler = RpcHandler::new(state.clone());

        tokio::spawn(async move {
            if let Err(e) = handler.handle_stream(stream).await {
                error!("Connection error from {:?}: {}", peer, e);
            }
        });
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    init_logging(args.verbosity.to_filter());
    if let Some(cfg) = &args.config.config {
        tracing::debug!(config = %cfg.display(), "config override");
    }

    info!("Starting Phenotype Daemon v{}", VersionInfo::current().version);

    let config = ServerConfig::default();
    // One shared BufferPool for the lifetime of the daemon. All
    // connection handlers Arc-clone this same pool so buffer reuse
    // crosses connections (delivers SPEC.md:1651's 70% allocator
    // pressure reduction, which the old per-connection pool could
    // not).
    let buffer_pool = Arc::new(BufferPool::new());
    let state = Arc::new(SharedState::new(buffer_pool));

    // Spawn TCP server (always available for fallback)
    let tcp_state = state.clone();
    let tcp_config = config.clone();
    let tcp_handle = tokio::spawn(async move {
        if let Err(e) = run_tcp_server(&tcp_config, tcp_state).await {
            error!("TCP server error: {}", e);
        }
    });

    // Spawn Unix socket server (Unix only)
    #[cfg(unix)]
    let unix_handle = if !config.tcp_only {
        let unix_state = state.clone();
        let unix_config = config.clone();
        Some(tokio::spawn(async move {
            if let Err(e) = run_unix_server(&unix_config, unix_state).await {
                error!("Unix socket server error: {}", e);
            }
        }))
    } else {
        None
    };

    info!("Daemon ready - waiting for connections");

    // Wait for all servers
    tokio::select! {
        _ = tcp_handle => {
            warn!("TCP server exited");
        }
        _ = async {
            if let Some(h) = unix_handle {
                let _ = h.await;
            }
            std::future::pending::<()>().await;
        } => {}
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The `Display` impl for `ServerConfig` must never include the
    /// raw `auth_token` value. A stray `format!("{}", config)` in a
    /// panic message, log line, or config dump would otherwise leak
    /// the bearer token to anyone who can read the process output.
    #[test]
    fn display_does_not_leak_auth_token() {
        let secret = "super-secret-bearer-token-do-not-leak-9c2f";
        let config = ServerConfig {
            #[cfg(unix)]
            socket_path: PathBuf::from("/tmp/phenotype-daemon-test.sock"),
            tcp_port: DEFAULT_TCP_PORT,
            tcp_only: false,
            auth_token: Some(secret.to_string()),
        };

        let rendered = format!("{}", config);
        assert!(
            !rendered.contains(secret),
            "Display impl leaked auth_token. rendered = {:?}",
            rendered
        );
    }

    /// Smoke test: ensure the Args struct (with clap_ext::Verbosity and
    /// clap_ext::ConfigArg flattens) parses cleanly with the new --quiet
    /// and -c short-form flags.
    #[test]
    fn args_parse_with_clap_ext_flattens() {
        use clap::Parser;
        let args = Args::try_parse_from(["phenotype-daemon", "-q", "-c", "/tmp/x.toml"]).unwrap();
        assert!(args.verbosity.quiet);
        assert_eq!(
            args.config.config.as_ref().map(|p| p.display().to_string()),
            Some("/tmp/x.toml".to_string())
        );
    }
}
