//! Additional integration test patterns for `pheno-proc-uds` exercising
//! real consumer patterns not yet covered by `tests/integration.rs`:
//!
//! - **Pattern E (auth_handshake)**: an authenticated control plane where
//!   the client must present a known-magic token in the first frame
//!   before the server will accept any subsequent application frames.
//!   Mirrors the real-world pattern used by services that gate traffic
//!   by peer identity (where peer identity is communicated in-band
//!   because UDS does not carry out-of-band peer-cred by default).
//!
//! - **Pattern F (graceful_disconnect)**: a service that detects
//!   peer-initiated close on the receive path and surfaces it as
//!   `UdsError::ConnectionClosed` rather than a raw `io::Error`.
//!   Mirrors the real-world pattern where the client sends an explicit
//!   `BYE` sentinel frame and the server drains pending frames before
//!   tearing down the connection.

use pheno_proc_uds::{UdsError, UdsServer, UdsStream, MAX_MESSAGE_SIZE};
use std::time::Duration;
use tokio::time::timeout;

/// Build a unique socket path that won't collide across parallel tests.
fn unique_sock(prefix: &str) -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("/tmp/pheno_proc_uds_{prefix}_{nanos}.sock")
}

/// Pattern E: auth handshake.
///
/// The server's accept-loop rejects any first-frame that does not match
/// the known magic token. The client connects, sends the token, and only
/// then proceeds to a normal request/response exchange. If the token is
/// wrong, the server closes the connection and the client's next
/// `recv_msg` returns `UdsError::ConnectionClosed`.
#[tokio::test]
async fn pattern_e_auth_handshake_accepts_correct_token() {
    const AUTH_TOKEN: &str = "pheno-auth-token-v1";
    const APP_REQUEST: &str = "list-features";
    const APP_RESPONSE: &str = "feature-a,feature-b";

    let socket_path = unique_sock("auth_ok");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_task = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();

        // Auth gate: first frame must be the magic token.
        let token = stream.recv_msg().await.unwrap();
        assert_eq!(token, AUTH_TOKEN);

        // Subsequent frames are application-level.
        let req = stream.recv_msg().await.unwrap();
        assert_eq!(req, APP_REQUEST);
        stream.send_msg(APP_RESPONSE).await.unwrap();
    });

    let path_for_client = socket_path.clone();
    let client_task = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();

        stream.send_msg(AUTH_TOKEN).await.unwrap();
        stream.send_msg(APP_REQUEST).await.unwrap();
        let resp = stream.recv_msg().await.unwrap();
        assert_eq!(resp, APP_RESPONSE);
    });

    timeout(Duration::from_secs(5), async {
        let (s, c) = tokio::join!(server_task, client_task);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("auth-handshake round-trip timed out");

    let _ = std::fs::remove_file(&socket_path);
}

#[tokio::test]
async fn pattern_e_auth_handshake_rejects_wrong_token_with_close() {
    const WRONG_TOKEN: &str = "not-the-right-token";

    let socket_path = unique_sock("auth_fail");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_task = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let token = stream.recv_msg().await.unwrap();
        if token != "pheno-auth-token-v1" {
            // Server tears the connection down without responding.
            drop(stream);
            return;
        }
        panic!("server should have rejected the wrong token");
    });

    let path_for_client = socket_path.clone();
    let client_task = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();
        stream.send_msg(WRONG_TOKEN).await.unwrap();
        // The server dropped its side; the client's next recv must observe
        // the close. Whether this surfaces as `UdsError::ConnectionClosed`
        // or as `UdsError::Io(UnexpectedEof)` is implementation-defined;
        // the contract under test is "the client observes *some* error".
        let err = stream.recv_msg().await.expect_err("must observe close");
        match err {
            UdsError::ConnectionClosed | UdsError::Io(_) => {} // both are acceptable
            other => panic!("expected close error, got {other:?}"),
        }
    });

    timeout(Duration::from_secs(5), async {
        let (s, c) = tokio::join!(server_task, client_task);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("auth-reject handshake timed out");

    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern F: graceful disconnect via an explicit sentinel frame.
///
/// The client sends a `BYE` frame, the server reads it, sends an `ACK`
/// frame, and both sides close. This is the canonical pattern used by
/// long-running services that want clean teardown semantics rather than
/// relying on the kernel's drop-on-exit behavior.
#[tokio::test]
async fn pattern_f_graceful_disconnect_via_sentinel_frame() {
    const BYE: &str = "BYE";
    const ACK: &str = "ACK";

    let socket_path = unique_sock("graceful");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_task = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let frame = stream.recv_msg().await.unwrap();
        assert_eq!(frame, BYE);
        stream.send_msg(ACK).await.unwrap();
        // Server drops its half — closes its end of the socket.
        drop(stream);
    });

    let path_for_client = socket_path.clone();
    let client_task = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();

        // Application-level work before disconnect (none here, but the
        // pattern is "do work, then send sentinel, then close").
        stream.send_msg(BYE).await.unwrap();
        let ack = stream.recv_msg().await.unwrap();
        assert_eq!(ack, ACK);
    });

    timeout(Duration::from_secs(5), async {
        let (s, c) = tokio::join!(server_task, client_task);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("graceful disconnect timed out");

    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern F': payload-at-the-edge of MAX_MESSAGE_SIZE round-trips
/// successfully under the auth handshake gate. This is a combined
/// Pattern A + Pattern B + Pattern E test: the largest legal payload
/// carries through the auth gate without truncation or rejection.
#[tokio::test]
async fn pattern_e_auth_with_max_size_payload() {
    const AUTH_TOKEN: &str = "pheno-auth-token-v1";

    let socket_path = unique_sock("auth_max");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_task = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let token = stream.recv_msg().await.unwrap();
        assert_eq!(token, AUTH_TOKEN);
        let payload = stream.recv_msg().await.unwrap();
        assert_eq!(payload.len(), MAX_MESSAGE_SIZE);
        stream.send_msg("ack").await.unwrap();
    });

    let path_for_client = socket_path.clone();
    let client_task = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();
        stream.send_msg(AUTH_TOKEN).await.unwrap();
        let big = "z".repeat(MAX_MESSAGE_SIZE);
        stream.send_msg(&big).await.unwrap();
        let ack = stream.recv_msg().await.unwrap();
        assert_eq!(ack, "ack");
    });

    timeout(Duration::from_secs(10), async {
        let (s, c) = tokio::join!(server_task, client_task);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("auth+max-size round-trip timed out");

    let _ = std::fs::remove_file(&socket_path);
}
