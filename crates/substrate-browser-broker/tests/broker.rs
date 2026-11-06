//! End-to-end broker tests: isolation, exclusivity, release, and the viewer.

use std::{sync::Arc, time::Duration};

use substrate_browser_broker::{router, Broker, Scope};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::TcpListener,
};

const PAGE: &str = "<html><head><title>Broker</title></head><body><h1>ok</h1></body></html>";

async fn serve_fixture() -> std::net::SocketAddr {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("addr");
    tokio::spawn(async move {
        loop {
            let Ok((mut socket, _)) = listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0u8; 4096];
                let _ = socket.read(&mut buffer).await;
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\n\
                     Connection: close\r\n\r\n{}",
                    PAGE.len(),
                    PAGE
                );
                let _ = socket.write_all(response.as_bytes()).await;
                let _ = socket.shutdown().await;
            });
        }
    });
    addr
}

fn has_browser() -> bool {
    substrate_browser_broker::browser_available()
}

#[tokio::test]
async fn concurrent_agents_on_separate_profiles_are_storage_isolated() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let addr = serve_fixture().await;
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");

    let alice = Scope::new("alice", "work", "s1").unwrap();
    let bob = Scope::new("bob", "work", "s1").unwrap();

    let first = broker
        .acquire(&alice, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire alice");
    let second = broker
        .acquire(&bob, "agent-b", Duration::from_secs(120))
        .await
        .expect("acquire bob");

    assert_ne!(first.data_dir, second.data_dir);

    first
        .browser
        .open(&format!("http://{addr}/"))
        .await
        .expect("open a");
    first
        .browser
        .eval("localStorage.setItem('who','alice')")
        .await
        .expect("set a");

    second
        .browser
        .open(&format!("http://{addr}/"))
        .await
        .expect("open b");
    let seen = second
        .browser
        .eval("localStorage.getItem('who')")
        .await
        .expect("get b");
    assert_eq!(
        seen,
        serde_json::Value::Null,
        "bob must not see alice's storage"
    );
    second
        .browser
        .eval("localStorage.setItem('who','bob')")
        .await
        .expect("set b");

    let live = broker.live().await;
    assert_eq!(live.len(), 2, "both sessions should be live and distinct");

    broker.release(first).await.expect("release a");
    broker.release(second).await.expect("release b");
    assert!(broker.live().await.is_empty());
}

#[tokio::test]
async fn a_leased_profile_cannot_be_acquired_twice() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").unwrap();

    let held = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("first acquire");

    let second_attempt = broker
        .acquire(
            &Scope::new("alice", "work", "s2").unwrap(),
            "agent-b",
            Duration::from_secs(120),
        )
        .await;
    assert!(second_attempt.is_err(), "a second writer must be refused");
    assert_eq!(
        broker.live().await.len(),
        1,
        "the refused acquire must not leak a session"
    );

    broker.release(held).await.expect("release");
}

#[tokio::test]
async fn release_frees_the_profile_for_the_next_agent() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").unwrap();

    let held = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("first");
    let generation = held.generation;
    broker.release(held).await.expect("release");

    let sealed = broker
        .profiles()
        .generations("alice", "work")
        .expect("generations")
        .into_iter()
        .find(|entry| entry.id == generation)
        .expect("generation recorded");
    assert!(sealed.sealed, "releasing must seal the generation");

    let next = broker
        .acquire(&scope, "agent-b", Duration::from_secs(120))
        .await
        .expect("second agent can take over");
    broker.release(next).await.expect("release again");
}

#[tokio::test]
async fn viewer_serves_the_exact_lease_and_rejects_unknown_or_unauthorised() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let addr = serve_fixture().await;
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let held = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire");

    held.browser
        .open(&format!("http://{addr}/"))
        .await
        .expect("open");

    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let viewer_addr = listener.local_addr().expect("addr");
    let app = router(broker.clone(), Some("s3cret".to_string()));
    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    tokio::time::sleep(Duration::from_millis(150)).await;

    let client = reqwest::Client::new();
    let base = format!("http://{viewer_addr}");

    // Health is open.
    assert_eq!(
        client
            .get(format!("{base}/healthz"))
            .send()
            .await
            .unwrap()
            .status(),
        200
    );

    // Without the token, everything else is refused.
    assert_eq!(
        client
            .get(format!("{base}/v1/view/{}/png", held.lease.id))
            .send()
            .await
            .unwrap()
            .status(),
        401
    );

    // With the token, the exact lease renders a PNG.
    let png = client
        .get(format!("{base}/v1/view/{}/png", held.lease.id))
        .header("Authorization", "Bearer s3cret")
        .send()
        .await
        .expect("viewer request")
        .bytes()
        .await
        .expect("body");
    assert_eq!(&png[..8], b"\x89PNG\r\n\x1a\n", "viewer must return a PNG");

    // A lease that is not live is a 404, not somebody else's browser.
    assert_eq!(
        client
            .get(format!("{base}/v1/view/lease-nope/png"))
            .header("Authorization", "Bearer s3cret")
            .send()
            .await
            .unwrap()
            .status(),
        404
    );

    // The session listing names the lease.
    let sessions: serde_json::Value = client
        .get(format!("{base}/v1/sessions"))
        .header("Authorization", "Bearer s3cret")
        .send()
        .await
        .unwrap()
        .json()
        .await
        .unwrap();
    let listed = sessions["sessions"].as_array().expect("sessions array");
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0]["lease_id"], held.lease.id);

    broker.release(held).await.expect("release");
}
