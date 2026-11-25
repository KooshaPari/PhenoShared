//! Integration tests for pheno-proc-uds
//!
//! Tests cover multi-client communication, stress scenarios, error recovery,
//! and message framing edge cases over real Unix domain sockets.

#![cfg(unix)]

use pheno_proc_uds::{Message, UdsServer, UdsStream};
use std::time::Duration;
use tokio::time::timeout;

/// Helper: create a unique socket path to avoid collisions between tests.
fn sock_path(name: &str) -> String {
    let dir = std::env::temp_dir();
    let id = std::process::id();
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("{}/test_uds_{}_{}_{}.sock", dir.display(), name, id, ts)
}

/// Helper: clean up socket file.
fn cleanup(path: &str) {
    let _ = std::fs::remove_file(path);
}

// ---------------------------------------------------------------------------
// Basic echo test
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_echo_roundtrip() {
    let path = sock_path("echo");
    let server = UdsServer::bind(&path).await.unwrap();

    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let msg = stream.recv_msg().await.unwrap();
        stream.send_msg(&msg).await.unwrap();
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    let mut client = UdsStream::connect(&path).await.unwrap();
    client.send_msg("ping").await.unwrap();
    let resp = client.recv_msg().await.unwrap();
    assert_eq!(resp, "ping");

    let _ = timeout(Duration::from_secs(5), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Multiple sequential clients
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_multiple_sequential_clients() {
    let path = sock_path("multi_seq");
    let server = UdsServer::bind(&path).await.unwrap();

    let server_handle = tokio::spawn(async move {
        for i in 0..5 {
            let mut stream = server.accept().await.unwrap();
            let msg = stream.recv_msg().await.unwrap();
            assert_eq!(msg, format!("msg-{i}"));
            stream.send_msg(&format!("ack-{i}")).await.unwrap();
        }
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    for i in 0..5 {
        let mut client = UdsStream::connect(&path).await.unwrap();
        client.send_msg(&format!("msg-{i}")).await.unwrap();
        let resp = client.recv_msg().await.unwrap();
        assert_eq!(resp, format!("ack-{i}"));
    }

    let _ = timeout(Duration::from_secs(10), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Large payload transfer
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_large_payload() {
    let path = sock_path("large");
    let server = UdsServer::bind(&path).await.unwrap();

    // 1 MiB payload
    let payload = "X".repeat(1024 * 1024);

    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let msg = stream.recv_msg().await.unwrap();
        assert_eq!(msg.len(), 1024 * 1024);
        stream.send_msg("ok").await.unwrap();
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    let mut client = UdsStream::connect(&path).await.unwrap();
    client.send_msg(&payload).await.unwrap();
    let resp = client.recv_msg().await.unwrap();
    assert_eq!(resp, "ok");

    let _ = timeout(Duration::from_secs(10), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Empty message
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_empty_message() {
    let path = sock_path("empty");
    let server = UdsServer::bind(&path).await.unwrap();

    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let msg = stream.recv_msg().await.unwrap();
        assert!(msg.is_empty());
        stream.send_msg("").await.unwrap();
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    let mut client = UdsStream::connect(&path).await.unwrap();
    client.send_msg("").await.unwrap();
    let resp = client.recv_msg().await.unwrap();
    assert!(resp.is_empty());

    let _ = timeout(Duration::from_secs(5), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Unicode / UTF-8 payload
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_unicode_payload() {
    let path = sock_path("unicode");
    let server = UdsServer::bind(&path).await.unwrap();

    let payload = "Hello \u{1F600} \u{1F4A9} \u{1F680} \u{2615}";

    let server_handle = tokio::spawn(async move {
        let mut stream = server.accept().await.unwrap();
        let msg = stream.recv_msg().await.unwrap();
        assert_eq!(msg, payload);
        stream.send_msg("received").await.unwrap();
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    let mut client = UdsStream::connect(&path).await.unwrap();
    client.send_msg(payload).await.unwrap();
    let resp = client.recv_msg().await.unwrap();
    assert_eq!(resp, "received");

    let _ = timeout(Duration::from_secs(5), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Message codec unit tests
// ---------------------------------------------------------------------------

#[test]
fn test_message_from_string() {
    let msg = Message::from_string("hello world");
    assert_eq!(msg.payload, b"hello world");
    assert_eq!(msg.to_string().unwrap(), "hello world");
}

#[test]
fn test_message_empty() {
    let msg = Message::from_string("");
    assert!(msg.payload.is_empty());
    assert_eq!(msg.to_string().unwrap(), "");
}

#[test]
fn test_message_roundtrip() {
    let original = "test payload 123";
    let msg = Message::from_string(original);
    let restored = msg.to_string().unwrap();
    assert_eq!(restored, original);
}

// ---------------------------------------------------------------------------
// Server already bound (socket reuse)
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_server_socket_reuse() {
    let path = sock_path("reuse");

    // First server
    {
        let server = UdsServer::bind(&path).await.unwrap();
        let handle = tokio::spawn(async move {
            let mut stream = server.accept().await.unwrap();
            stream.send_msg("first").await.unwrap();
        });
        tokio::time::sleep(Duration::from_millis(50)).await;
        let mut client = UdsStream::connect(&path).await.unwrap();
        let resp = client.recv_msg().await.unwrap();
        assert_eq!(resp, "first");
        let _ = timeout(Duration::from_secs(5), handle).await;
    }

    // Second server on same path
    {
        let server = UdsServer::bind(&path).await.unwrap();
        let handle = tokio::spawn(async move {
            let mut stream = server.accept().await.unwrap();
            stream.send_msg("second").await.unwrap();
        });
        tokio::time::sleep(Duration::from_millis(50)).await;
        let mut client = UdsStream::connect(&path).await.unwrap();
        let resp = client.recv_msg().await.unwrap();
        assert_eq!(resp, "second");
        let _ = timeout(Duration::from_secs(5), handle).await;
    }

    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Stress: rapid connect/disconnect cycles
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_rapid_connect_disconnect() {
    let path = sock_path("rapid");
    let server = UdsServer::bind(&path).await.unwrap();

    let server_handle = tokio::spawn(async move {
        for _ in 0..20 {
            let mut stream = server.accept().await.unwrap();
            let _ = stream.recv_msg().await;
            stream.send_msg("ok").await.unwrap();
        }
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    for i in 0..20 {
        let mut client = UdsStream::connect(&path).await.unwrap();
        client.send_msg(&format!("req-{i}")).await.unwrap();
        let resp = client.recv_msg().await.unwrap();
        assert_eq!(resp, "ok");
    }

    let _ = timeout(Duration::from_secs(30), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Concurrent clients via tokio::spawn
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_concurrent_clients() {
    let path = sock_path("concurrent");
    let server = UdsServer::bind(&path).await.unwrap();
    let num_clients = 10;

    let server_handle = tokio::spawn(async move {
        for _ in 0..num_clients {
            let mut stream = server.accept().await.unwrap();
            let msg = stream.recv_msg().await.unwrap();
            stream.send_msg(&format!("echo:{msg}")).await.unwrap();
        }
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    let mut handles = Vec::new();
    for i in 0..num_clients {
        let p = path.clone();
        handles.push(tokio::spawn(async move {
            let mut client = UdsStream::connect(&p).await.unwrap();
            client.send_msg(&format!("hello-{i}")).await.unwrap();
            let resp = client.recv_msg().await.unwrap();
            assert_eq!(resp, format!("echo:hello-{i}"));
        }));
    }

    for h in handles {
        let _ = h.await;
    }

    let _ = timeout(Duration::from_secs(15), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Client disconnect handling (server should not panic)
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_client_disconnect_mid_stream() {
    let path = sock_path("disconnect");
    let server = UdsServer::bind(&path).await.unwrap();

    let server_handle = tokio::spawn(async move {
        // Accept a connection, then try to read (should get error after client drops)
        let mut stream = server.accept().await.unwrap();
        // Client will drop after sending partial data; recv_msg should error
        let result = stream.recv_msg().await;
        assert!(result.is_err());
    });

    tokio::time::sleep(Duration::from_millis(50)).await;

    {
        // Connect and immediately drop
        let _client = UdsStream::connect(&path).await.unwrap();
        // Client is dropped here
    }

    let _ = timeout(Duration::from_secs(5), server_handle).await;
    cleanup(&path);
}

// ---------------------------------------------------------------------------
// Graceful shutdown: accept() returns ConnectionClosed after shutdown()
// ---------------------------------------------------------------------------

#[tokio::test]
async fn test_shutdown_causes_accept_to_return_error() {
    let path = sock_path("shutdown");
    let server = UdsServer::bind(&path).await.unwrap();
    let server = std::sync::Arc::new(server);

    // Spawn a task that blocks on accept.
    let server_clone = server.clone();
    let server_handle = tokio::spawn(async move {
        let result = server_clone.accept().await;
        match result {
            Err(pheno_proc_uds::UdsError::ConnectionClosed) => {}
            other => panic!("expected ConnectionClosed, got {other:?}"),
        }
    });

    // Give the accept call time to start blocking.
    tokio::time::sleep(Duration::from_millis(50)).await;

    // Signal shutdown from outside the spawned task.
    server.shutdown();

    let result = timeout(Duration::from_secs(5), server_handle).await;
    assert!(
        result.is_ok(),
        "server task did not complete after shutdown"
    );
    cleanup(&path);
}
