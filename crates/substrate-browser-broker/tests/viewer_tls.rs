//! TLS behaviour of the `brokerd` binary.
//!
//! These tests drive the real binary, so they exercise the real flag parsing,
//! the real rustls handshake, and the unchanged router. A self-signed
//! certificate is generated at test time and written to a temporary directory.

use std::{
    net::TcpListener,
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    time::Duration,
};

use tempfile::TempDir;

/// Kill the broker when the test ends, whatever happened.
struct BrokerProcess(Child);

impl Drop for BrokerProcess {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

fn brokerd() -> &'static str {
    env!("CARGO_BIN_EXE_brokerd")
}

/// Ask the OS for a port that is free right now, then release it.
fn free_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
    let port = listener.local_addr().expect("ephemeral addr").port();
    drop(listener);
    port
}

/// Write a throwaway self-signed certificate/key pair and return their paths.
fn self_signed(dir: &Path) -> (PathBuf, PathBuf) {
    let generated = rcgen::generate_simple_self_signed(vec![
        "localhost".to_string(),
        "127.0.0.1".to_string(),
    ])
    .expect("generate self-signed certificate");
    let cert = dir.join("cert.pem");
    let key = dir.join("key.pem");
    std::fs::write(&cert, generated.cert.pem()).expect("write certificate");
    std::fs::write(&key, generated.key_pair.serialize_pem()).expect("write private key");
    (cert, key)
}

fn run_brokerd(args: &[&str]) -> std::process::Output {
    Command::new(brokerd())
        .args(args)
        .stdin(Stdio::null())
        .output()
        .expect("run brokerd")
}

#[test]
fn cert_without_key_fails_closed() {
    let dir = TempDir::new().expect("temp dir");
    let (cert, _key) = self_signed(dir.path());
    let root = dir.path().join("state");

    let output = run_brokerd(&[
        "--root",
        root.to_str().unwrap(),
        "--bind",
        "127.0.0.1:0",
        "--tls-cert",
        cert.to_str().unwrap(),
    ]);

    assert_eq!(
        output.status.code(),
        Some(2),
        "a lone --tls-cert must be rejected; stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("--tls-key"),
        "the error should name the missing flag; got: {stderr}"
    );
}

#[test]
fn key_without_cert_fails_closed() {
    let dir = TempDir::new().expect("temp dir");
    let (_cert, key) = self_signed(dir.path());
    let root = dir.path().join("state");

    let output = run_brokerd(&[
        "--root",
        root.to_str().unwrap(),
        "--bind",
        "127.0.0.1:0",
        "--tls-key",
        key.to_str().unwrap(),
    ]);

    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("--tls-cert"),
        "the error should name the missing flag; got: {stderr}"
    );
}

#[test]
fn empty_tls_path_fails_closed() {
    let dir = TempDir::new().expect("temp dir");
    let root = dir.path().join("state");

    let output = run_brokerd(&[
        "--root",
        root.to_str().unwrap(),
        "--bind",
        "127.0.0.1:0",
        "--tls-cert",
        " ",
        "--tls-key",
        " ",
    ]);

    assert_eq!(output.status.code(), Some(2));
}

#[test]
fn non_loopback_tls_without_token_still_refused() {
    let dir = TempDir::new().expect("temp dir");
    let (cert, key) = self_signed(dir.path());
    let root = dir.path().join("state");
    let bind = format!("0.0.0.0:{}", free_port());

    let output = run_brokerd(&[
        "--root",
        root.to_str().unwrap(),
        "--bind",
        &bind,
        "--tls-cert",
        cert.to_str().unwrap(),
        "--tls-key",
        key.to_str().unwrap(),
    ]);

    assert_eq!(
        output.status.code(),
        Some(2),
        "TLS does not replace the token requirement for non-loopback binds"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("without a bearer token"),
        "got: {stderr}"
    );
}

#[tokio::test]
async fn https_requires_the_bearer_token() {
    let dir = TempDir::new().expect("temp dir");
    let (cert, key) = self_signed(dir.path());
    let root = dir.path().join("state");
    let port = free_port();
    let bind = format!("127.0.0.1:{port}");
    let token = "s3cret-viewer-token";

    let child = Command::new(brokerd())
        .args([
            "--root",
            root.to_str().unwrap(),
            "--bind",
            &bind,
            "--token",
            token,
            "--tls-cert",
            cert.to_str().unwrap(),
            "--tls-key",
            key.to_str().unwrap(),
        ])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .expect("spawn brokerd");
    let _broker = BrokerProcess(child);

    // The certificate is throwaway, so trust it blindly: what is being proven
    // is that a TLS handshake completes and the router answers behind it.
    let client = reqwest::Client::builder()
        .danger_accept_invalid_certs(true)
        .build()
        .expect("build client");

    let health = format!("https://127.0.0.1:{port}/healthz");
    let leases = format!("https://127.0.0.1:{port}/v1/leases");

    let mut ready = false;
    for _ in 0..200 {
        if let Ok(resp) = client.get(&health).send().await {
            if resp.status().is_success() {
                ready = true;
                break;
            }
        }
        tokio::time::sleep(Duration::from_millis(50)).await;
    }
    assert!(ready, "brokerd never answered HTTPS on {bind}");

    let with_token = client
        .get(&leases)
        .bearer_auth(token)
        .send()
        .await
        .expect("request with token");
    assert_eq!(with_token.url().scheme(), "https");
    assert_eq!(
        with_token.status(),
        reqwest::StatusCode::OK,
        "the correct bearer token must be accepted over TLS"
    );

    let without_token = client.get(&leases).send().await.expect("request");
    assert_eq!(
        without_token.status(),
        reqwest::StatusCode::UNAUTHORIZED,
        "an absent bearer token must be rejected over TLS"
    );

    let wrong_token = client
        .get(&leases)
        .bearer_auth("not-the-token")
        .send()
        .await
        .expect("request");
    assert_eq!(
        wrong_token.status(),
        reqwest::StatusCode::UNAUTHORIZED,
        "a wrong bearer token must be rejected over TLS"
    );

    // A plaintext client must not get a 200 from a TLS listener.
    let plain = reqwest::Client::new()
        .get(format!("http://127.0.0.1:{port}/healthz"))
        .send()
        .await;
    if let Ok(resp) = plain {
        assert_ne!(
            resp.status(),
            reqwest::StatusCode::OK,
            "plain HTTP must not be served when TLS is enabled"
        );
    }
}
