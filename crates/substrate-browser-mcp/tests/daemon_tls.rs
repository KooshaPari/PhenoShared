//! The daemon's TLS certificate, and the CA this client pins to reach it.
//!
//! The daemon under test is the real `substrate_browser_broker::router_with`,
//! served over HTTPS with a throwaway self-signed certificate. What is under
//! test is the client's trust decision: a pinned certificate is accepted, an
//! unpinned one is refused with an error that names the variable to set, and
//! a mis-pointed variable is refused before the request leaves the process.

use std::{
    collections::BTreeMap,
    io::{self, BufReader},
    net::SocketAddr,
    path::{Path, PathBuf},
    sync::Arc,
    time::Duration,
};

use axum::{serve::Listener, Router};
use tokio::net::{TcpListener, TcpStream};
use tokio_rustls::{
    rustls::{pki_types::CertificateDer, ServerConfig},
    TlsAcceptor,
};

use substrate_browser_broker::{router_with, Broker};
use substrate_browser_mcp::{BrokerTools, RemoteConfig, CA_ENV};

/// Write a throwaway self-signed certificate and key, and return their paths.
///
/// The certificate names `127.0.0.1` as an IP address, because the client
/// below checks the name the daemon presents.
fn self_signed(dir: &Path) -> (PathBuf, PathBuf) {
    let generated =
        rcgen::generate_simple_self_signed(vec!["localhost".to_string(), "127.0.0.1".to_string()])
            .expect("generate a self-signed certificate");
    let cert = dir.join("cert.pem");
    let key = dir.join("key.pem");
    std::fs::write(&cert, generated.cert.pem()).expect("write the certificate");
    std::fs::write(&key, generated.key_pair.serialize_pem()).expect("write the private key");
    (cert, key)
}

/// Select the process-wide rustls provider.
///
/// The workspace links exactly one backend, so this is normally already
/// unambiguous; installing it explicitly keeps the test from depending on
/// which provider another crate happened to pull in.
fn install_provider() {
    let _ = tokio_rustls::rustls::crypto::ring::default_provider().install_default();
}

/// The TLS configuration for the daemon's certificate.
fn server_config(cert: &Path, key: &Path) -> ServerConfig {
    let certs: Vec<CertificateDer<'static>> = rustls_pemfile::certs(&mut BufReader::new(
        std::fs::File::open(cert).expect("open the certificate"),
    ))
    .collect::<Result<Vec<_>, _>>()
    .expect("read the certificate");
    let key = rustls_pemfile::private_key(&mut BufReader::new(
        std::fs::File::open(key).expect("open the private key"),
    ))
    .expect("read the private key")
    .expect("the file holds a private key");
    ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(certs, key)
        .expect("the certificate and the key belong together")
}

/// A listener that completes the TLS handshake before yielding a stream.
struct TlsListener {
    inner: TcpListener,
    acceptor: TlsAcceptor,
}

impl Listener for TlsListener {
    type Io = tokio_rustls::server::TlsStream<TcpStream>;
    type Addr = SocketAddr;

    async fn accept(&mut self) -> (Self::Io, Self::Addr) {
        loop {
            let (tcp, addr) = match self.inner.accept().await {
                Ok(pair) => pair,
                Err(err) => {
                    eprintln!("test daemon: accept failed: {err}");
                    tokio::time::sleep(Duration::from_millis(50)).await;
                    continue;
                },
            };
            match self.acceptor.accept(tcp).await {
                Ok(stream) => return (stream, addr),
                Err(err) => {
                    // A client that refuses the certificate is the case under
                    // test, not a reason to stop serving.
                    eprintln!("test daemon: the handshake was refused: {err}");
                    continue;
                },
            }
        }
    }

    fn local_addr(&self) -> io::Result<Self::Addr> {
        self.inner.local_addr()
    }
}

/// Serve `app` over HTTPS on an ephemeral loopback port.
async fn serve_https(app: Router, cert: &Path, key: &Path) -> String {
    install_provider();
    let acceptor = TlsAcceptor::from(Arc::new(server_config(cert, key)));
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind an ephemeral port");
    let address = listener.local_addr().expect("local address");
    let listener = TlsListener {
        inner: listener,
        acceptor,
    };
    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    format!("https://{address}")
}

/// A daemon holding `broker`, reachable over HTTPS.
async fn daemon(broker: &Arc<Broker>, cert: &Path, key: &Path) -> String {
    serve_https(
        router_with(Arc::clone(broker), None, BTreeMap::new()),
        cert,
        key,
    )
    .await
}

/// The pinned certificate is the daemon's identity: the client trusts exactly
/// the certificate the daemon was started with, and reaches it without
/// anything being installed into the machine's trust store.
#[tokio::test]
async fn a_pinned_certificate_reaches_the_daemon() {
    let dir = tempfile::tempdir().expect("temp dir");
    let (cert, key) = self_signed(dir.path());
    let broker = Arc::new(Broker::new(dir.path().join("state")).expect("broker"));
    let base = daemon(&broker, &cert, &key).await;

    let tools = BrokerTools::open_remote(RemoteConfig::new(base.clone(), None).with_ca(&cert))
        .expect("the pinned certificate is readable");

    let status = tools.status().await.expect("the daemon answers");
    assert_eq!(
        status.brokerd.as_deref(),
        Some(base.as_str()),
        "the snapshot names the daemon it came from"
    );
    assert_eq!(status.root, base);
}

/// Without a pinned certificate the daemon's certificate is refused, and the
/// error names the variable that would repair it. That is not an unreachable
/// daemon: the daemon answered the handshake and this client turned the
/// certificate down.
#[tokio::test]
async fn an_unpinned_certificate_is_refused_with_the_variable_to_set() {
    let dir = tempfile::tempdir().expect("temp dir");
    let (cert, key) = self_signed(dir.path());
    let broker = Arc::new(Broker::new(dir.path().join("state")).expect("broker"));
    let base = daemon(&broker, &cert, &key).await;

    let tools = BrokerTools::open_remote(RemoteConfig::new(base, None)).expect("open the client");

    let err = tools
        .status()
        .await
        .expect_err("a certificate the client does not trust must be refused");
    let message = err.to_string();
    assert!(
        message.contains(CA_ENV),
        "the error must name the variable to set: {message}"
    );
    assert!(
        !message.to_lowercase().contains("unreachable"),
        "a refused certificate is not an unreachable daemon: {message}"
    );
}

/// A path that holds no certificate is refused before the request leaves the
/// process, and the error names both the variable and the path.
#[tokio::test]
async fn a_missing_ca_file_is_refused_before_any_request() {
    let dir = tempfile::tempdir().expect("temp dir");
    let (cert, key) = self_signed(dir.path());
    let broker = Arc::new(Broker::new(dir.path().join("state")).expect("broker"));
    let base = daemon(&broker, &cert, &key).await;

    let absent = dir.path().join("absent-ca.pem");
    let Err(err) = BrokerTools::open_remote(RemoteConfig::new(base, None).with_ca(&absent)) else {
        panic!("a CA file that is not there must be refused");
    };

    let message = err.to_string();
    assert!(
        message.contains(CA_ENV),
        "the error must name the variable to fix: {message}"
    );
    assert!(
        message.contains(absent.to_str().expect("a utf-8 path")),
        "the error must name the path: {message}"
    );
    assert!(
        !message.to_lowercase().contains("unreachable"),
        "a CA file that cannot be read is not an unreachable daemon: {message}"
    );
}

/// A path this process cannot read is refused in its own words, again
/// before any request leaves the process.
#[tokio::test]
async fn an_unreadable_ca_path_is_refused() {
    let dir = tempfile::tempdir().expect("temp dir");
    // A directory in the certificate's place: the read fails for every user,
    // unlike a permission bit that a privileged process can walk past.
    let unreadable = dir.path().join("ca-is-a-directory");
    std::fs::create_dir(&unreadable).expect("create the directory");

    let Err(err) = BrokerTools::open_remote(
        RemoteConfig::new("https://127.0.0.1:1", None).with_ca(&unreadable),
    ) else {
        panic!("a CA path that cannot be read must be refused");
    };

    let message = err.to_string();
    assert!(
        message.contains(CA_ENV),
        "the error must name the variable to fix: {message}"
    );
    assert!(
        message.contains(unreadable.to_str().expect("a utf-8 path")),
        "the error must name the path: {message}"
    );
    assert!(
        !message.to_lowercase().contains("unreachable"),
        "a CA path that cannot be read is not an unreachable daemon: {message}"
    );
}

/// A file that is not a PEM certificate is refused in its own words, again
/// before any request leaves the process.
#[tokio::test]
async fn a_file_that_is_not_a_certificate_is_refused() {
    let dir = tempfile::tempdir().expect("temp dir");
    let junk = dir.path().join("not-a-certificate.pem");
    std::fs::write(&junk, b"this file holds no certificate").expect("write the file");

    let Err(err) =
        BrokerTools::open_remote(RemoteConfig::new("https://127.0.0.1:1", None).with_ca(&junk))
    else {
        panic!("a file that holds no certificate must be refused");
    };

    let message = err.to_string();
    assert!(
        message.contains(CA_ENV),
        "the error must name the variable to fix: {message}"
    );
    assert!(
        message.contains(junk.to_str().expect("a utf-8 path")),
        "the error must name the path: {message}"
    );
    assert!(
        !message.to_lowercase().contains("unreachable"),
        "a CA file that holds no certificate is not an unreachable daemon: {message}"
    );
}

/// A PEM block whose body is not a certificate is refused as well, so a
/// truncated or mangled file is never mistaken for a trust anchor.
#[tokio::test]
async fn a_mangled_certificate_is_refused() {
    let dir = tempfile::tempdir().expect("temp dir");
    let mangled = dir.path().join("mangled-certificate.pem");
    std::fs::write(
        &mangled,
        "-----BEGIN CERTIFICATE-----\nnot a certificate at all\n-----END CERTIFICATE-----\n",
    )
    .expect("write the file");

    let Err(err) =
        BrokerTools::open_remote(RemoteConfig::new("https://127.0.0.1:1", None).with_ca(&mangled))
    else {
        panic!("a mangled certificate must be refused");
    };

    let message = err.to_string();
    assert!(
        message.contains(CA_ENV),
        "the error must name the variable to fix: {message}"
    );
    assert!(
        message.contains(mangled.to_str().expect("a utf-8 path")),
        "the error must name the path: {message}"
    );
    assert!(
        !message.to_lowercase().contains("unreachable"),
        "a mangled certificate is not an unreachable daemon: {message}"
    );
}
