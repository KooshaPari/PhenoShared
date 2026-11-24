//! The MCP bridge acting on a running `brokerd`.
//!
//! Unlike `remote_backend.rs` - which uses a fake server to pin the *decision*
//! not to invent a local authority - these tests serve the real
//! `substrate_browser_broker::router_with` on a real loopback socket and drive it
//! with the real [`BrokerTools`] remote backend. Client and server therefore
//! agree on the wire contract or these fail.
//!
//! Leases are granted straight through the daemon's authority in the tests that
//! do not need a browser, which is exactly the state a `brokerd` restart leaves
//! behind: a lease record with no live browser. The tests that acquire a real
//! browser say so in their names and report a skip when no Chrome-family binary
//! is present.

use std::{collections::BTreeMap, sync::Arc, time::Duration};

use substrate_browser::Scope;
use substrate_browser_broker::{router_with, Broker};
use substrate_browser_mcp::{
    kind_of, AcquireParams, BrokerTools, RemoteConfig, TOKEN_ENV, URL_ENV,
};

const TOKEN: &str = "daemon-token";

/// Serve `app` on an ephemeral loopback port and return its base URL.
async fn serve(app: axum::Router) -> String {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind an ephemeral port");
    let address = listener.local_addr().expect("local address");
    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    format!("http://{address}")
}

/// A daemon holding `broker`, reachable at the returned URL.
async fn daemon(broker: &Arc<Broker>) -> String {
    serve(router_with(
        Arc::clone(broker),
        Some(TOKEN.to_string()),
        BTreeMap::new(),
    ))
    .await
}

fn scope(principal: &str, profile: &str) -> Scope {
    Scope::new(principal, profile, "default").expect("valid scope")
}

/// Tools that talk to the daemon, not to a local broker.
fn tools(base: &str) -> BrokerTools {
    BrokerTools::open_remote(RemoteConfig::new(base, Some(TOKEN.to_string())))
        .expect("open the remote backend")
}

/// Port 1 is reserved and never served, so connecting there is refused at once.
const UNREACHABLE_DAEMON: &str = "http://127.0.0.1:1";

#[tokio::test]
async fn release_through_the_daemon_releases_the_daemons_lease() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    let lease = broker
        .leases()
        .grant(
            &scope("alice", "work"),
            "daemon-holder",
            Duration::from_secs(60),
        )
        .expect("grant a lease");
    let base = daemon(&broker).await;
    let tools = tools(&base);

    assert!(
        tools.broker().is_none(),
        "a remote instance must own no local broker"
    );

    let outcome = tools
        .release(&lease.id, lease.fencing_token)
        .await
        .expect("the daemon releases its own lease");

    assert!(outcome.released);
    assert_eq!(outcome.lease_id, lease.id);
    assert!(
        outcome.teardown.contains("lease record revoked"),
        "the daemon's teardown report must be passed through verbatim: {}",
        outcome.teardown
    );
    assert!(
        broker.leases().list().expect("list leases").is_empty(),
        "the daemon's lease store must really be empty afterwards"
    );
}

#[tokio::test]
async fn a_stale_fencing_token_is_refused_by_the_daemon() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    let lease = broker
        .leases()
        .grant(
            &scope("alice", "work"),
            "daemon-holder",
            Duration::from_secs(60),
        )
        .expect("grant a lease");
    let base = daemon(&broker).await;
    let tools = tools(&base);

    let err = tools
        .release(&lease.id, lease.fencing_token + 1)
        .await
        .expect_err("a stale token must not release anything");
    assert_eq!(kind_of(&err), "Refused");
    let message = err.to_string();
    assert!(
        message.contains("409") && message.contains("stale fencing token"),
        "the daemon's refusal must reach the caller: {message}"
    );

    // Fail-closed: the lease is untouched, and still releasable with the real
    // token.
    assert_eq!(broker.leases().list().expect("list leases").len(), 1);
    let outcome = tools
        .release(&lease.id, lease.fencing_token)
        .await
        .expect("the correct token still works");
    assert!(outcome.released);
}

#[tokio::test]
async fn purge_through_the_daemon_keeps_the_daemons_guards() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    broker
        .profiles()
        .ensure("alice", "work")
        .expect("materialise the profile");
    let profile_dir = broker.profiles().profile_dir("alice", "work");
    let base = daemon(&broker).await;
    let tools = tools(&base);

    // The daemon, not the client, owns the confirmation guard.
    let err = tools
        .purge("alice", "work", false)
        .await
        .expect_err("purge without confirmation must be refused");
    assert_eq!(kind_of(&err), "Refused");
    assert!(
        err.to_string().contains("confirm"),
        "the refusal must name the missing confirmation: {err}"
    );
    assert!(profile_dir.exists(), "a refused purge deletes nothing");

    // And the lease guard.
    let lease = broker
        .leases()
        .grant(
            &scope("alice", "work"),
            "daemon-holder",
            Duration::from_secs(60),
        )
        .expect("grant a lease");
    let err = tools
        .purge("alice", "work", true)
        .await
        .expect_err("purging a leased profile must be refused");
    assert!(
        err.to_string().contains("leased"),
        "the refusal must name the lease: {err}"
    );
    assert!(profile_dir.exists());

    broker.leases().revoke(&lease.id).expect("revoke");
    let outcome = tools
        .purge("alice", "work", true)
        .await
        .expect("a confirmed purge of an unleased profile");
    assert!(outcome.purged && outcome.existed);
    assert!(!profile_dir.exists(), "the daemon deleted the profile data");
}

#[tokio::test]
async fn reap_through_the_daemon_reports_the_daemons_counts() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    let base = daemon(&broker).await;
    let tools = tools(&base);

    // Nothing to reap yet; the call still round-trips and reports honestly.
    let outcome = tools.reap().await.expect("reap through the daemon");
    assert_eq!(outcome.reaped, 0);
    assert_eq!(outcome.leases_reaped, 0);
    assert_eq!(outcome.live_sessions_after, 0);
}

#[tokio::test]
async fn an_unreachable_daemon_fails_loudly_for_every_mutation() {
    let tools = BrokerTools::open_remote(RemoteConfig::new(UNREACHABLE_DAEMON, None))
        .expect("building the client is not I/O");

    let acquire = tools
        .acquire(AcquireParams {
            principal: "alice".into(),
            profile: "work".into(),
            session: None,
            holder: None,
            ttl_ms: None,
            annotations: Default::default(),
        })
        .await
        .expect_err("acquire must fail loudly");
    let release = tools
        .release("lease-1", 1)
        .await
        .expect_err("release must fail loudly");
    let reap = tools.reap().await.expect_err("reap must fail loudly");
    let purge = tools
        .purge("alice", "work", true)
        .await
        .expect_err("purge must fail loudly");

    for err in [&acquire, &release, &reap, &purge] {
        assert_eq!(kind_of(err), "Refused", "{err}");
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
            "the error must name the variable to fix: {message}"
        );
    }
}

#[tokio::test]
async fn acquire_then_release_through_the_daemon_when_a_browser_is_available() {
    if !substrate_browser_broker::browser_available() {
        eprintln!("skipping: no browser");
        return;
    }

    let dir = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    let base = daemon(&broker).await;
    let tools = tools(&base);

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
        .expect("the daemon acquires the browser");

    assert!(!acquired.lease_id.is_empty());
    assert!(acquired.fencing_token >= 1);
    assert!(
        !acquired.data_dir.is_empty(),
        "the daemon reports where it put the browser"
    );
    assert_eq!(
        broker.live().await.len(),
        1,
        "the browser belongs to the daemon, not to this process"
    );
    assert!(
        tools
            .live()
            .await
            .iter()
            .any(|session| session.lease_id == acquired.lease_id),
        "the daemon's own listing shows the session"
    );

    let released = tools
        .release(&acquired.lease_id, acquired.fencing_token)
        .await
        .expect("release through the daemon");
    assert!(released.released);
    assert_eq!(
        released.teardown, "browser closed; lease revoked; generation sealed",
        "the daemon reports a full teardown"
    );
    assert!(
        broker.live().await.is_empty(),
        "no live session may outlive the release"
    );
}

/// The client must present the credential on **every** request, mutations
/// included. A 401 rather than a silent local fallback is the correct behaviour.
#[tokio::test]
async fn mutations_without_the_token_are_rejected_by_the_daemon() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = Arc::new(Broker::new(dir.path()).expect("broker"));
    let base = daemon(&broker).await;
    let tokenless =
        BrokerTools::open_remote(RemoteConfig::new(base, None)).expect("open the remote backend");

    let err = tokenless
        .reap()
        .await
        .expect_err("an unauthenticated mutation must fail");
    assert_eq!(kind_of(&err), "Refused");
    assert!(
        err.to_string().contains("401"),
        "the error must report the daemon's 401: {err}"
    );
    let message = err.to_string();
    assert!(
        message.contains(TOKEN_ENV),
        "the error must name the variable that carries the token: {message}"
    );
}
