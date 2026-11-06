//! Integration tests for `pheno-proc-uds`.
//!
//! These tests exercise the public surface (`UdsServer`, `UdsStream`,
//! `MAX_MESSAGE_SIZE`) under realistic consumer patterns:
//!
//! - Multi-frame request/response on a single connection (the
//!   server-actor / client-actor pattern a long-lived IPC consumer uses).
//! - The `MAX_MESSAGE_SIZE` boundary at exactly-N, exactly-N+1, and far
//!   past N (consumer sends + ack-channel check).
//! - Two clients sharing one listener (server-side accept-loop pattern).
//!
//! These tests are written without naming any specific in-workspace
//! consumer (there is none today; `pheno-cli` is Go). They prove the
//! public contract that any Rust consumer would observe.

use pheno_proc_uds::{UdsServer, UdsStream, MAX_MESSAGE_SIZE};
use std::time::Duration;
use tokio::time::timeout;

fn unique_sock(name: &str) -> String {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!(
        "/tmp/pheno_proc_uds_test_{}_{}_{}.sock",
        name,
        std::process::id(),
        nanos
    )
}

/// Pattern A: long-lived connection with multiple request/response cycles
/// on the same `UdsStream`. This is the canonical consumer pattern.
#[tokio::test]
async fn integration_long_lived_multi_frame_roundtrip() {
    let socket_path = unique_sock("long_lived");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();

    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        for i in 0..5u32 {
            let req = stream.recv_msg().await.unwrap();
            assert_eq!(req, format!("req-{i}"));
            stream.send_msg(&format!("resp-{i}")).await.unwrap();
        }
    });

    let path_for_client = socket_path.clone();
    let client_handle = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();
        for i in 0..5u32 {
            stream.send_msg(&format!("req-{i}")).await.unwrap();
            let resp = stream.recv_msg().await.unwrap();
            assert_eq!(resp, format!("resp-{i}"));
        }
    });

    timeout(Duration::from_secs(5), async {
        let (s, c) = tokio::join!(server_handle, client_handle);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("long-lived multi-frame round-trip timed out");

    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern B: explicit `MAX_MESSAGE_SIZE` boundary on the receive side —
/// exactly `MAX_MESSAGE_SIZE` bytes payload → accepted.
#[tokio::test]
async fn integration_recv_accepts_exactly_max_size() {
    let socket_path = unique_sock("recv_max");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let req = stream.recv_msg().await.unwrap();
        assert_eq!(req.len(), MAX_MESSAGE_SIZE);
        stream.send_msg("ack-ok").await.unwrap();
    });

    let path_for_client = socket_path.clone();
    let client_handle = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();
        let big = "a".repeat(MAX_MESSAGE_SIZE);
        stream.send_msg(&big).await.unwrap();
        let ack = stream.recv_msg().await.unwrap();
        assert_eq!(ack, "ack-ok");
    });

    timeout(Duration::from_secs(10), async {
        let (s, c) = tokio::join!(server_handle, client_handle);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("exactly-max-size round-trip timed out");

    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern B': explicit `MAX_MESSAGE_SIZE + 1` peer-supplied length prefix
/// is rejected with `MessageTooLarge { size: MAX + 1, max: MAX }` on receive.
/// This is the negative oracle that proves the pre-allocation guard.
#[tokio::test]
async fn integration_recv_rejects_oversized_length_prefix() {
    let socket_path = unique_sock("recv_reject");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let err = stream
            .recv_msg()
            .await
            .expect_err("must reject oversized prefix");
        match err {
            pheno_proc_uds::UdsError::MessageTooLarge { size, max } => {
                assert_eq!(size, MAX_MESSAGE_SIZE + 1);
                assert_eq!(max, MAX_MESSAGE_SIZE);
            }
            other => panic!("expected MessageTooLarge, got {other:?}"),
        }
    });

    let path_for_client = socket_path.clone();
    let client_handle = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();
        // Use the public raw-byte `send` to write only the length prefix
        // (no payload) — the server must reject before reading any body.
        let oversized_len = (MAX_MESSAGE_SIZE as u32 + 1).to_be_bytes();
        stream.send(&oversized_len).await.unwrap();
    });

    timeout(Duration::from_secs(5), async {
        let (s, c) = tokio::join!(server_handle, client_handle);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("oversized-prefix rejection timed out");

    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern B'': explicit `MAX_MESSAGE_SIZE + 1` outbound payload on the
/// send side is rejected with the same error before any framing header
/// is written.
#[tokio::test]
async fn integration_send_rejects_oversized_payload() {
    let socket_path = unique_sock("send_reject");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_handle = tokio::spawn(async move {
        let _ = server.accept().await;
    });

    tokio::time::sleep(Duration::from_millis(20)).await;
    let mut client = UdsStream::connect(&socket_path).await.unwrap();
    let oversized = "x".repeat(MAX_MESSAGE_SIZE + 1);
    let err = client
        .send_msg(&oversized)
        .await
        .expect_err("must reject oversized outbound payload");
    match err {
        pheno_proc_uds::UdsError::MessageTooLarge { size, max } => {
            assert_eq!(size, MAX_MESSAGE_SIZE + 1);
            assert_eq!(max, MAX_MESSAGE_SIZE);
        }
        other => panic!("expected MessageTooLarge, got {other}"),
    }

    drop(server_handle);
    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern C: server-side accept-loop with two concurrent clients.
/// Each client gets its own dedicated request/response; neither should
/// observe the other's frame. This proves per-connection isolation.
#[tokio::test]
async fn integration_two_clients_one_server() {
    let socket_path = unique_sock("two_clients");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();

    let server_task = tokio::spawn(async move {
        for _ in 0..2 {
            let mut stream = server.accept().await.unwrap();
            tokio::spawn(async move {
                let msg = stream.recv_msg().await.unwrap();
                stream.send_msg(&format!("echo:{msg}")).await.unwrap();
            });
        }
    });

    async fn run_client(socket_path: String, label: &str) -> String {
        let mut stream = UdsStream::connect(&socket_path).await.unwrap();
        stream.send_msg(label).await.unwrap();
        stream.recv_msg().await.unwrap()
    }

    let client_a = tokio::spawn({
        let p = socket_path.clone();
        async move { run_client(p, "alpha").await }
    });
    let client_b = tokio::spawn({
        let p = socket_path.clone();
        async move { run_client(p, "beta").await }
    });

    timeout(Duration::from_secs(5), async {
        let a = client_a.await.unwrap();
        let b = client_b.await.unwrap();
        server_task.await.unwrap();
        assert_eq!(a, "echo:alpha");
        assert_eq!(b, "echo:beta");
    })
    .await
    .expect("two-clients round-trip timed out");

    let _ = std::fs::remove_file(&socket_path);
}

/// Pattern D: empty-payload message round-trips correctly (boundary on
/// the lower edge, separate from `MAX_MESSAGE_SIZE` upper edge).
#[tokio::test]
async fn integration_empty_payload_roundtrip() {
    let socket_path = unique_sock("empty");
    let _ = std::fs::remove_file(&socket_path);

    let server = UdsServer::bind(&socket_path).await.unwrap();
    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let req = stream.recv_msg().await.unwrap();
        assert_eq!(req, "");
        stream.send_msg("").await.unwrap();
    });

    let path_for_client = socket_path.clone();
    let client_handle = tokio::spawn(async move {
        tokio::time::sleep(Duration::from_millis(20)).await;
        let mut stream = UdsStream::connect(&path_for_client).await.unwrap();
        stream.send_msg("").await.unwrap();
        let resp = stream.recv_msg().await.unwrap();
        assert_eq!(resp, "");
    });

    timeout(Duration::from_secs(5), async {
        let (s, c) = tokio::join!(server_handle, client_handle);
        s.unwrap();
        c.unwrap();
    })
    .await
    .expect("empty-payload round-trip timed out");

    let _ = std::fs::remove_file(&socket_path);
}
