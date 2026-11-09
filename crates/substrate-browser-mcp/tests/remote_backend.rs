//! Remote-authority behaviour of the MCP tool layer.
//!
//! No browser and no real `brokerd`: either the daemon address is deliberately
//! unreachable, or a tiny in-test HTTP server answers the same read endpoints
//! `brokerd` serves. What is under test is the decision this crate must never
//! get wrong - when a daemon is configured, the tools must act on *that*
//! authority, never quietly on a local one.

use std::sync::{Arc, Mutex};

use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::TcpListener,
};

use substrate_browser_mcp::{
    kind_of, AcquireParams, BrokerTools, RemoteConfig, TOKEN_ENV, URL_ENV,
};

const LEASES_BODY: &str = r#"{
  "leases": [
    {
      "id": "lease-daemon-1",
      "principal": "agent-a",
      "profile": "work",
      "session": "default",
      "tab": null,
      "holder": "daemon-holder",
      "fencing_token": 7,
      "issued_at_unix_ms": 1000,
      "expires_at_unix_ms": 9999999999999,
      "owner_pid": 4242
    }
  ]
}"#;

const SESSIONS_BODY: &str = r#"{
  "sessions": [
    {
      "lease_id": "lease-daemon-1",
      "holder": "daemon-holder",
      "scope": "agent-a/work",
      "generation": 3,
      "expires_at_unix_ms": 9999999999999
    }
  ]
}"#;

/// Serve `brokerd`'s two read endpoints on an ephemeral loopback port.
///
/// Returns the base URL and every request head the server saw, so a test can
/// assert the bearer token and the path that was actually used.
async fn spawn_fake_brokerd() -> (String, Arc<Mutex<Vec<String>>>) {
    let listener = TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind an ephemeral port");
    let address = listener.local_addr().expect("local address");
    let seen = Arc::new(Mutex::new(Vec::new()));
    let seen_in_server = Arc::clone(&seen);

    tokio::spawn(async move {
        while let Ok((mut socket, _)) = listener.accept().await {
            let seen = Arc::clone(&seen_in_server);
            tokio::spawn(async move {
                let mut request = Vec::new();
                let mut chunk = [0u8; 1024];
                // Read until the head is complete; requests here are tiny.
                while !request.windows(4).any(|w| w == b"\r\n\r\n") {
                    match socket.read(&mut chunk).await {
                        Ok(0) | Err(_) => break,
                        Ok(n) => request.extend_from_slice(&chunk[..n]),
                    }
                }
                let head = String::from_utf8_lossy(&request).to_string();
                let path = head
                    .lines()
                    .next()
                    .and_then(|line| line.split_whitespace().nth(1))
                    .unwrap_or("/")
                    .to_string();
                seen.lock().expect("request log").push(head);

                let body = if path == "/v1/leases" {
                    LEASES_BODY
                } else if path == "/v1/sessions" {
                    SESSIONS_BODY
                } else {
                    "{}"
                };
                let response = format!(
                    "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n\
                     content-length: {}\r\nconnection: close\r\n\r\n{body}",
                    body.len()
                );
                let _ = socket.write_all(response.as_bytes()).await;
                let _ = socket.flush().await;
            });
        }
    });

    (format!("http://{address}"), seen)
}

/// Port 1 is reserved and never served, so connecting there is refused at once.
const UNREACHABLE_DAEMON: &str = "http://127.0.0.1:1";

#[tokio::test]
async fn unreachable_daemon_fails_loudly_instead_of_using_a_local_broker() {
    let tools = BrokerTools::open_remote(RemoteConfig::new(UNREACHABLE_DAEMON, None))
        .expect("building the client is not I/O");

    // The decisive assertion: no in-process broker exists to fall back to.
    assert!(
        tools.broker().is_none(),
        "remote mode must own no local broker"
    );
    assert_eq!(tools.authority(), format!("brokerd:{UNREACHABLE_DAEMON}"));

    let err = tools
        .status()
        .await
        .expect_err("an unreachable configured daemon must be an error");

    assert_eq!(kind_of(&err), "Refused");
    let message = err.to_string();
    assert!(
        message.contains("unreachable"),
        "the error must say the daemon is unreachable: {message}"
    );
    assert!(
        message.contains("refusing to fall back to an in-process broker"),
        "the error must name the fallback it refused: {message}"
    );
    assert!(
        message.contains(URL_ENV),
        "the error must name the env var to fix: {message}"
    );
}

#[tokio::test]
async fn status_and_live_are_served_by_the_running_daemon() {
    let (url, seen) = spawn_fake_brokerd().await;
    let tools = BrokerTools::open_remote(RemoteConfig::new(url.clone(), Some("s3cret".into())))
        .expect("open remote tools");

    let status = tools.status().await.expect("status from the daemon");
    assert_eq!(
        status.root, url,
        "the snapshot names the daemon it came from"
    );
    assert_eq!(status.brokerd.as_deref(), Some(url.as_str()));
    assert_eq!(
        status.browser_available, None,
        "a daemon host's browser inventory is not visible from here"
    );
    assert_eq!(status.live_sessions, 1);
    assert_eq!(status.active_leases.len(), 1);
    let lease = &status.active_leases[0];
    assert_eq!(lease.lease_id, "lease-daemon-1");
    assert_eq!(lease.holder, "daemon-holder");
    assert_eq!(lease.fencing_token, 7);
    assert_eq!(lease.scope, "agent-a/work");
    assert!(!lease.expired);

    let live = tools.live().await;
    assert_eq!(live.len(), 1);
    assert_eq!(live[0].lease_id, "lease-daemon-1");
    assert_eq!(live[0].generation, 3);

    // The bearer token really was presented, on both read endpoints.
    let requests = seen.lock().expect("request log");
    let paths: Vec<&str> = requests
        .iter()
        .filter_map(|head| head.lines().next())
        .filter_map(|line| line.split_whitespace().nth(1))
        .collect();
    assert!(paths.contains(&"/v1/leases"), "paths: {paths:?}");
    assert!(paths.contains(&"/v1/sessions"), "paths: {paths:?}");
    for head in requests.iter() {
        assert!(
            head.to_ascii_lowercase()
                .contains("authorization: bearer s3cret"),
            "every request must carry the configured token: {head}"
        );
    }
}

#[tokio::test]
async fn mutations_are_refused_when_a_daemon_is_configured() {
    let (url, _seen) = spawn_fake_brokerd().await;
    let tools =
        BrokerTools::open_remote(RemoteConfig::new(url.clone(), None)).expect("open remote tools");

    let acquire = tools
        .acquire(AcquireParams {
            principal: "agent-a".into(),
            profile: "work".into(),
            session: None,
            holder: None,
            ttl_ms: None,
            annotations: Default::default(),
        })
        .await
        .expect_err("acquire must not invent a local authority");
    assert_eq!(kind_of(&acquire), "Refused");
    assert!(
        acquire.to_string().contains("no broker_acquire route"),
        "the refusal must name the missing route: {acquire}"
    );

    let release = tools
        .release("lease-daemon-1", 7)
        .await
        .expect_err("release must not invent a local authority");
    assert_eq!(kind_of(&release), "Refused");

    let reap = tools
        .reap()
        .await
        .expect_err("reap must not invent a local authority");
    assert_eq!(kind_of(&reap), "Refused");

    let purge = tools
        .purge("agent-a", "work", true)
        .await
        .expect_err("purge must not invent a local authority");
    assert_eq!(kind_of(&purge), "Refused");
    assert!(
        purge.to_string().contains("read-only"),
        "the refusal must explain the read-only surface: {purge}"
    );

    for err in [&acquire, &release, &reap, &purge] {
        assert!(
            err.to_string().contains(URL_ENV),
            "the refusal must name {URL_ENV}: {err}"
        );
    }
}

#[test]
fn daemon_config_precedence_and_normalisation() {
    fn lookup(vars: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let vars: std::collections::BTreeMap<String, String> = vars
            .iter()
            .map(|(key, value)| ((*key).to_string(), (*value).to_string()))
            .collect();
        move |name: &str| vars.get(name).cloned()
    }

    // No daemon configured: the bridge stays local (that is the only path where
    // a local broker is opened at all).
    assert!(RemoteConfig::from_lookup(lookup(&[])).is_none());
    // A blank value is the same as unset, not "the empty daemon".
    assert!(RemoteConfig::from_lookup(lookup(&[(URL_ENV, "  ")])).is_none());

    let config = RemoteConfig::from_lookup(lookup(&[
        (URL_ENV, "http://127.0.0.1:8787/"),
        (TOKEN_ENV, "tok"),
    ]))
    .expect("configured");
    assert_eq!(config.base_url(), "http://127.0.0.1:8787");
    assert!(config.has_token());

    // An empty token is "no token", not an empty bearer credential.
    let config = RemoteConfig::from_lookup(lookup(&[(URL_ENV, "http://h"), (TOKEN_ENV, "")]))
        .expect("configured");
    assert_eq!(config.base_url(), "http://h");
    assert!(!config.has_token());

    // The token never leaks through Debug.
    let with_token = RemoteConfig::new("http://h", Some("tok-secret".into()));
    let debug = format!("{with_token:?}");
    assert!(
        !debug.contains("tok-secret"),
        "debug must redact the token: {debug}"
    );
    assert!(debug.contains("<redacted>"), "debug: {debug}");
}
