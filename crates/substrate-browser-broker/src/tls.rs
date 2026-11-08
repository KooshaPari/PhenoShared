//! Opt-in TLS for `brokerd`.
//!
//! TLS is mutual-exclusive with the plain-HTTP path: the process either has a
//! complete certificate/key pair or none at all. A half-configured pair fails
//! closed rather than silently serving cleartext, and the caller keeps using
//! [`substrate_browser_broker::serve`] when no TLS material was given.
//!
//! The transport itself is tiny: a [`TlsListener`] wraps the TCP listener and
//! performs the handshake before handing the stream to `axum::serve`, so the
//! router and every route stay exactly as they are.

use std::{
    fs, io,
    path::{Path, PathBuf},
    sync::Arc,
};

use axum::{serve::Listener, Router};
use tokio::net::{TcpListener, TcpStream};
use tokio_rustls::{
    rustls::{
        pki_types::{CertificateDer, PrivateKeyDer},
        ServerConfig,
    },
    TlsAcceptor,
};

/// A complete certificate/key pair supplied on the command line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TlsConfig {
    /// PEM bundle: the leaf certificate followed by any intermediates.
    pub cert: PathBuf,
    /// PEM private key (PKCS#8, PKCS#1, or SEC1).
    pub key: PathBuf,
}

/// Why a TLS configuration could not be used.
#[derive(Debug, thiserror::Error)]
pub enum TlsError {
    /// Only one of the two paths was given.
    #[error("--tls-cert and --tls-key must be given together (missing {missing})")]
    Incomplete {
        /// The flag that was not supplied.
        missing: &'static str,
    },
    /// A path was supplied but empty.
    #[error("--tls-cert and --tls-key must not be empty")]
    Empty,
    /// The file could not be read.
    #[error("cannot read TLS {what} at {path}: {source}")]
    Read {
        /// `certificate` or `private key`.
        what: &'static str,
        /// The offending path.
        path: PathBuf,
        /// Underlying I/O error.
        source: io::Error,
    },
    /// The PEM file parsed but contained no usable item.
    #[error("no {what} found in {path}")]
    NoMaterial {
        /// `certificate` or `private key`.
        what: &'static str,
        /// The offending path.
        path: PathBuf,
    },
    /// The PEM did not parse, or cert and key do not belong together.
    #[error("invalid TLS {what} in {path}: {detail}")]
    Invalid {
        /// `certificate`, `private key`, or `certificate/key pair`.
        what: &'static str,
        /// The offending path.
        path: PathBuf,
        /// Parser or rustls detail.
        detail: String,
    },
    /// Binding the listening socket failed.
    #[error(transparent)]
    Io(#[from] io::Error),
}

impl TlsConfig {
    /// Resolve the `--tls-cert` / `--tls-key` flags.
    ///
    /// `Ok(None)` means "no TLS was requested" and the caller must keep the
    /// existing plain-HTTP behaviour. Anything half-specified is an error, so a
    /// typo can never downgrade a remote bind to cleartext.
    pub fn from_flags(cert: Option<String>, key: Option<String>) -> Result<Option<Self>, TlsError> {
        match (cert, key) {
            (None, None) => Ok(None),
            (Some(_), None) => Err(TlsError::Incomplete {
                missing: "--tls-key",
            }),
            (None, Some(_)) => Err(TlsError::Incomplete {
                missing: "--tls-cert",
            }),
            (Some(cert), Some(key)) => {
                if cert.trim().is_empty() || key.trim().is_empty() {
                    return Err(TlsError::Empty);
                }
                Ok(Some(Self {
                    cert: PathBuf::from(cert),
                    key: PathBuf::from(key),
                }))
            },
        }
    }

    /// Load the PEM chain and private key into a rustls server configuration.
    pub fn server_config(&self) -> Result<ServerConfig, TlsError> {
        let certs = load_certs(&self.cert)?;
        let key = load_key(&self.key)?;
        ServerConfig::builder()
            .with_no_client_auth()
            .with_single_cert(certs, key)
            .map_err(|err| TlsError::Invalid {
                what: "certificate/key pair",
                path: self.cert.clone(),
                detail: err.to_string(),
            })
    }
}

fn read_pem(path: &Path, what: &'static str) -> Result<Vec<u8>, TlsError> {
    fs::read(path).map_err(|source| TlsError::Read {
        what,
        path: path.to_path_buf(),
        source,
    })
}

fn load_certs(path: &Path) -> Result<Vec<CertificateDer<'static>>, TlsError> {
    let pem = read_pem(path, "certificate")?;
    let mut reader = io::BufReader::new(pem.as_slice());
    let certs = rustls_pemfile::certs(&mut reader)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|err| TlsError::Invalid {
            what: "certificate",
            path: path.to_path_buf(),
            detail: err.to_string(),
        })?;
    if certs.is_empty() {
        return Err(TlsError::NoMaterial {
            what: "certificate",
            path: path.to_path_buf(),
        });
    }
    Ok(certs)
}

fn load_key(path: &Path) -> Result<PrivateKeyDer<'static>, TlsError> {
    let pem = read_pem(path, "private key")?;
    let mut reader = io::BufReader::new(pem.as_slice());
    rustls_pemfile::private_key(&mut reader)
        .map_err(|err| TlsError::Invalid {
            what: "private key",
            path: path.to_path_buf(),
            detail: err.to_string(),
        })?
        .ok_or_else(|| TlsError::NoMaterial {
            what: "private key",
            path: path.to_path_buf(),
        })
}

/// A TCP listener that completes a TLS handshake before yielding a stream.
///
/// `axum::serve` only needs [`Listener`], so this is the whole integration
/// surface: the router is served identically over HTTP and HTTPS.
struct TlsListener {
    inner: TcpListener,
    acceptor: TlsAcceptor,
}

impl Listener for TlsListener {
    type Io = tokio_rustls::server::TlsStream<TcpStream>;
    type Addr = std::net::SocketAddr;

    async fn accept(&mut self) -> (Self::Io, Self::Addr) {
        loop {
            let (tcp, addr) = match self.inner.accept().await {
                Ok(pair) => pair,
                Err(err) => {
                    // Mirrors axum's own accept loop: back off, never spin.
                    eprintln!("brokerd: accept failed: {err}");
                    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
                    continue;
                },
            };
            match self.acceptor.accept(tcp).await {
                Ok(stream) => return (stream, addr),
                Err(err) => {
                    // One bad or probing client is not fatal.
                    eprintln!("brokerd: TLS handshake from {addr} failed: {err}");
                    continue;
                },
            }
        }
    }

    fn local_addr(&self) -> io::Result<Self::Addr> {
        self.inner.local_addr()
    }
}

/// Select the process-wide rustls provider.
///
/// The workspace links exactly one backend, so this is normally already
/// unambiguous; installing it explicitly keeps the binary working if another
/// crate in the graph ever pulls in a second provider. A provider that is
/// already installed wins, which is why the error is ignored.
fn install_crypto_provider() {
    let _ = tokio_rustls::rustls::crypto::ring::default_provider().install_default();
}

/// Serve `app` over HTTPS on `bind` until the process is stopped.
pub async fn serve_tls(bind: &str, app: Router, config: &TlsConfig) -> Result<(), TlsError> {
    install_crypto_provider();
    let acceptor = TlsAcceptor::from(Arc::new(config.server_config()?));
    let listener = TlsListener {
        inner: TcpListener::bind(bind).await?,
        acceptor,
    };
    axum::serve(listener, app).await?;
    Ok(())
}
