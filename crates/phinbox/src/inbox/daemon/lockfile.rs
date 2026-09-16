//! Lockfile management for the inbox daemon.
//!
//! The daemon writes a small JSON lockfile (`daemon.lock`) at startup so
//! other processes can discover the running daemon's port and bind address.
//! The lockfile is also used as a shutdown signal — `stop()` touches the
//! file to wake the HTTP loop's mtime poll.

use std::net::{IpAddr, SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::time::Duration;

use serde::{Deserialize, Serialize};

use crate::inbox::unix_now_ms;

/// The lockfile name. Holds the listening socket address + boot time.
pub const LOCKFILE_NAME: &str = "daemon.lock";

/// Payload stored in the lockfile so other processes can discover the
/// running daemon.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LockfilePayload {
    pub root: PathBuf,
    pub port: u16,
    pub bind: IpAddr,
    pub booted_at_ms: u64,
    /// Path to the daemon's JSON-RPC Unix domain socket. `None` if the
    /// daemon was started before IPC support shipped; clients should fall
    /// back to HTTP in that case.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub ipc_sock: Option<PathBuf>,
}

/// Write a lockfile with the daemon's listen address, boot time, and
/// (optional) IPC socket path.
pub(crate) fn write_lockfile(
    path: &Path,
    root: &Path,
    port: u16,
    bind: IpAddr,
    ipc_sock: Option<&Path>,
) -> Result<(), crate::error::ElicitError> {
    let payload = LockfilePayload {
        root: root.to_path_buf(),
        port,
        bind,
        booted_at_ms: unix_now_ms(),
        ipc_sock: ipc_sock.map(Path::to_path_buf),
    };
    let json = serde_json::to_vec_pretty(&payload).map_err(crate::error::ElicitError::Json)?;
    std::fs::write(path, json)?;
    Ok(())
}

/// Read and parse an existing lockfile. Returns `None` if the file is
/// missing or corrupt.
#[must_use]
pub fn read_lockfile(root: &Path) -> Option<LockfilePayload> {
    let path = root.join(LOCKFILE_NAME);
    let bytes = std::fs::read(&path).ok()?;
    serde_json::from_slice(&bytes).ok()
}

/// Cheap "is anyone listening on this port?" probe.
pub(crate) fn is_port_live(bind: IpAddr, port: u16) -> bool {
    let addr = SocketAddr::new(bind, port);
    TcpStream::connect_timeout(&addr, Duration::from_millis(200)).is_ok()
}

/// Return the live URL of a running inbox daemon, if any. Reads the
/// daemon's lockfile and confirms the socket is actually accepting
/// connections. Returns `None` if no daemon is running or the lockfile
/// is stale (e.g. process died without cleanup).
///
/// `bind_filter` lets the caller restrict to a particular bind address
/// (loopback vs. LAN). Pass `None` to accept any bind address.
#[must_use]
pub fn live_url(root: &Path, bind_filter: Option<IpAddr>) -> Option<String> {
    let payload = read_lockfile(root)?;
    if let Some(addr) = bind_filter {
        if payload.bind != addr {
            return None;
        }
    }
    if !is_port_live(payload.bind, payload.port) {
        return None;
    }
    Some(format!("http://{}:{}", payload.bind, payload.port))
}
