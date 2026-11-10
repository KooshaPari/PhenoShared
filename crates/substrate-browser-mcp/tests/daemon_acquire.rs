//! Acceptance: an MCP `broker_acquire` through a running daemon must succeed,
//! quickly, without a browser being launched.
//!
//! This is the user-visible symptom that started the lazy-launch work: with
//! `BROKERD_URL` pointing at a live `brokerd`, `broker_acquire` used to fail.
//! Two faults stacked up:
//!
//! 1. the daemon launched Chrome inline, so a grant waited on a browser that
//!    could take 20-50s on a loaded host, and
//! 2. the client's 10s request timeout then aborted the call and reported the
//!    daemon as *unreachable*, hiding the real server-side error.
//!
//! The test drives the resolution the operator actually uses - `BROKERD_URL` plus
//! `BROKERD_TOKEN` and [`BrokerTools::open_default`] - against the real router on
//! a real loopback socket. It needs no Chrome binary, so it runs everywhere and
//! fails if a browser launch ever creeps back into acquire.

use std::{
    collections::BTreeMap,
    process::Command,
    sync::Arc,
    time::{Duration, Instant},
};

use substrate_browser_broker::{router_with, Broker};
use substrate_browser_mcp::{AcquireParams, BrokerTools, TOKEN_ENV, URL_ENV};

const TOKEN: &str = "daemon-token";

/// Every live process command line, or `None` when this host cannot report them.
fn process_command_lines() -> Option<String> {
    let output = Command::new("ps")
        .args(["-axww", "-o", "command"])
        .output()
        .ok()?;
    output
        .status
        .success()
        .then(|| String::from_utf8_lossy(&output.stdout).into_owned())
}

#[tokio::test]
async fn broker_acquire_through_the_daemon_succeeds_without_launching_a_browser() {
    // Serve the real daemon routes on an ephemeral loopback port.
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind an ephemeral port");
    let address = listener.local_addr().expect("local address");
    let state_root = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(state_root.path()).expect("broker"));
    let app = router_with(
        Arc::clone(&broker),
        Some(TOKEN.to_string()),
        BTreeMap::new(),
    );
    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    let base = format!("http://{address}");

    // Exactly what the operator configures for the remote path.
    std::env::set_var(URL_ENV, &base);
    std::env::set_var(TOKEN_ENV, TOKEN);
    let tools = BrokerTools::open_default().expect("open the remote backend");
    assert!(
        tools.broker().is_none(),
        "a configured daemon must own the authority: no local broker may exist"
    );

    let started = Instant::now();
    let acquired = tools
        .acquire(AcquireParams {
            principal: "alice".into(),
            profile: "work".into(),
            session: None,
            holder: None,
            ttl_ms: Some(120_000),
            annotations: Default::default(),
        })
        .await
        .expect("broker_acquire through the daemon must succeed");
    let elapsed = started.elapsed();
    eprintln!("broker_acquire through the daemon took {elapsed:?}");

    assert!(!acquired.lease_id.is_empty());
    assert!(acquired.fencing_token >= 1);
    assert_eq!(
        broker.live().await.len(),
        1,
        "the daemon published the session"
    );

    // A grant is a lease, not a browser launch: it must return well inside the
    // client's timeout, not merely "eventually".
    assert!(
        elapsed < Duration::from_secs(5),
        "acquire must not wait for a browser launch, took {elapsed:?}"
    );
    if let Some(lines) = process_command_lines() {
        assert!(
            !lines.contains(&acquired.data_dir),
            "acquire must not start a process against {}",
            acquired.data_dir
        );
    }

    let released = tools
        .release(&acquired.lease_id, acquired.fencing_token)
        .await
        .expect("release through the daemon");
    assert!(released.released);
    assert!(
        broker.live().await.is_empty(),
        "release must unpublish the session"
    );

    std::env::remove_var(URL_ENV);
    std::env::remove_var(TOKEN_ENV);
}
