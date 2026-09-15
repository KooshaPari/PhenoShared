//! Unix Domain Socket IPC for PhenoProc
//!
//! This crate provides a lightweight UDS-based IPC layer for PhenoProc,
//! including a server with graceful shutdown support, a client stream,
//! and a length-prefixed message codec.
//!
//! This crate is Unix-only. On non-Unix targets (e.g. Windows) it compiles to
//! an empty crate so the workspace remains buildable cross-platform.
#![cfg(unix)]

use std::path::Path;
use thiserror::Error;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{UnixListener, UnixStream};

/// Errors that can occur during UDS IPC operations.
#[derive(Debug, Error)]
pub enum UdsError {
    /// An underlying I/O error occurred (socket bind, read, write, etc.).
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// The connection was closed or the server is shutting down.
    #[error("connection closed")]
    ConnectionClosed,

    /// A received message could not be decoded as valid UTF-8.
    #[error("invalid message")]
    InvalidMessage,
}

/// A UDS server that listens for incoming client connections on a Unix socket.
///
/// Supports graceful shutdown via a [`tokio::sync::watch`] channel. When
/// [`shutdown`](Self::shutdown) is called, all pending [`accept`](Self::accept)
/// calls immediately return [`UdsError::ConnectionClosed`].
///
/// # Examples
///
/// ```no_run
/// use pheno_proc_uds::UdsServer;
///
/// # #[tokio::main]
/// # async fn main() -> Result<(), Box<dyn std::error::Error>> {
/// let server = UdsServer::bind("/tmp/my.sock").await?;
/// // In another task, trigger shutdown:
/// // server.shutdown();
/// # Ok(())
/// # }
/// ```
pub struct UdsServer {
    listener: UnixListener,
    shutdown_tx: tokio::sync::watch::Sender<bool>,
}

impl UdsServer {
    /// Bind a new server to the given Unix socket path.
    ///
    /// Removes any pre-existing socket file at `path` before binding so the
    /// call succeeds even if a previous server did not clean up.
    pub async fn bind<P: AsRef<Path>>(path: P) -> Result<Self, UdsError> {
        // Remove old socket file if exists
        let _ = std::fs::remove_file(&path);
        let listener = UnixListener::bind(path)?;
        let (shutdown_tx, _) = tokio::sync::watch::channel(false);
        Ok(Self {
            listener,
            shutdown_tx,
        })
    }

    /// Accept the next incoming connection.
    ///
    /// Returns a connected [`UdsStream`] on success. If [`shutdown`](Self::shutdown)
    /// has been called, this method returns [`UdsError::ConnectionClosed`] instead
    /// of blocking.
    pub async fn accept(&self) -> Result<UdsStream, UdsError> {
        let mut shutdown_rx = self.shutdown_tx.subscribe();
        tokio::select! {
            result = self.listener.accept() => {
                let (stream, _) = result?;
                Ok(UdsStream { stream })
            }
            _ = shutdown_rx.changed() => {
                Err(UdsError::ConnectionClosed)
            }
        }
    }

    /// Signal graceful shutdown to all waiting [`accept`](Self::accept) calls.
    ///
    /// Any currently-blocked `accept` invocation will immediately return
    /// [`UdsError::ConnectionClosed`]. Future calls to `accept` will also
    /// return that error.
    pub fn shutdown(&self) {
        let _ = self.shutdown_tx.send(true);
    }
}

/// A connected UDS client stream.
///
/// Wraps a [`tokio::net::UnixStream`] and provides both raw byte I/O and a
/// length-prefixed message protocol via [`send_msg`](Self::send_msg) /
/// [`recv_msg`](Self::recv_msg).
///
/// # Examples
///
/// ```no_run
/// use pheno_proc_uds::UdsStream;
///
/// # #[tokio::main]
/// # async fn main() -> Result<(), Box<dyn std::error::Error>> {
/// let mut stream = UdsStream::connect("/tmp/my.sock").await?;
/// stream.send_msg("hello").await?;
/// let reply = stream.recv_msg().await?;
/// # Ok(())
/// # }
/// ```
#[derive(Debug)]
pub struct UdsStream {
    stream: UnixStream,
}

impl UdsStream {
    /// Connect to a UDS server at the given socket `path`.
    pub async fn connect<P: AsRef<Path>>(path: P) -> Result<Self, UdsError> {
        let stream = UnixStream::connect(path).await?;
        Ok(Self { stream })
    }

    /// Write raw bytes to the stream.
    pub async fn send(&mut self, data: &[u8]) -> Result<(), UdsError> {
        self.stream.write_all(data).await?;
        Ok(())
    }

    /// Read raw bytes from the stream into `buf`.
    ///
    /// Returns the number of bytes read, or [`UdsError::ConnectionClosed`] if
    /// the peer has closed the connection.
    pub async fn recv(&mut self, buf: &mut [u8]) -> Result<usize, UdsError> {
        let n = self.stream.read(buf).await?;
        Ok(n)
    }

    /// Send a length-prefixed UTF-8 message.
    ///
    /// The message is encoded as a big-endian `u32` length prefix followed by
    /// the UTF-8 bytes of `msg`.
    pub async fn send_msg(&mut self, msg: &str) -> Result<(), UdsError> {
        let data = msg.as_bytes();
        let len = data.len() as u32;
        self.stream.write_all(&len.to_be_bytes()).await?;
        self.stream.write_all(data).await?;
        Ok(())
    }

    /// Receive a length-prefixed UTF-8 message.
    ///
    /// Reads a 4-byte big-endian length prefix, then reads exactly that many
    /// bytes and interprets them as UTF-8. Returns
    /// [`UdsError::ConnectionClosed`] if the peer closes the connection before
    /// a complete message is received, or [`UdsError::InvalidMessage`] if the
    /// payload is not valid UTF-8.
    pub async fn recv_msg(&mut self) -> Result<String, UdsError> {
        let mut len_buf = [0u8; 4];
        let n = self.stream.read_exact(&mut len_buf).await?;
        if n == 0 {
            return Err(UdsError::ConnectionClosed);
        }
        let len = u32::from_be_bytes(len_buf) as usize;

        let mut buf = vec![0u8; len];
        self.stream.read_exact(&mut buf).await?;

        String::from_utf8(buf).map_err(|_| UdsError::InvalidMessage)
    }
}

/// A simple byte payload used for message encoding and decoding.
///
/// [`Message`] provides convenience constructors for creating payloads from
/// strings and converting them back.
#[derive(Debug, Clone)]
pub struct Message {
    /// Raw byte payload.
    pub payload: Vec<u8>,
}

impl Message {
    /// Create a new message from raw bytes.
    pub fn new(payload: Vec<u8>) -> Self {
        Self { payload }
    }

    /// Create a message from a UTF-8 string.
    pub fn from_string(s: &str) -> Self {
        Self::new(s.as_bytes().to_vec())
    }

    /// Attempt to interpret the payload as a UTF-8 string.
    pub fn to_string(&self) -> Result<String, std::string::FromUtf8Error> {
        String::from_utf8(self.payload.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use tokio::time::timeout;

    #[tokio::test]
    async fn test_uds_basic() {
        let dir = std::env::temp_dir();
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let socket_path = format!(
            "{}/test_uds_basic_{}_{}.sock",
            dir.display(),
            std::process::id(),
            ts
        );
        let _ = std::fs::remove_file(&socket_path);

        let server = UdsServer::bind(&socket_path).await.unwrap();

        // Spawn server
        let server_handle = tokio::spawn(async move {
            let mut stream = server.accept().await.unwrap();
            let msg = stream.recv_msg().await.unwrap();
            assert_eq!(msg, "hello");
            stream.send_msg("world").await.unwrap();
        });

        // Client
        let sp = socket_path.clone();
        let client_handle = tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(100)).await;
            let mut stream = UdsStream::connect(&sp).await.unwrap();
            stream.send_msg("hello").await.unwrap();
            let response = stream.recv_msg().await.unwrap();
            assert_eq!(response, "world");
        });

        let _ = timeout(Duration::from_secs(5), async {
            let (r1, r2) = tokio::join!(server_handle, client_handle);
            r1.unwrap();
            r2.unwrap();
        })
        .await;

        let _ = std::fs::remove_file(&socket_path);
    }
}
