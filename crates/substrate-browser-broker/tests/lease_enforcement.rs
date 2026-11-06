//! Deterministic lease-enforcement tests: no browser is launched and no clock
//! sleeps, so these run everywhere and fail loudly if enforcement regresses.
use std::{
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Duration,
};

use substrate_browser_broker::{Broker, BrokerError, Clock, LeaseGuard, Scope};

struct ManualClock(AtomicU64);

impl ManualClock {
    fn new(now_unix_ms: u64) -> Arc<Self> {
        Arc::new(Self(AtomicU64::new(now_unix_ms)))
    }

    fn advance(&self, delta_ms: u64) {
        self.0.fetch_add(delta_ms, Ordering::SeqCst);
    }
}

impl Clock for ManualClock {
    fn now_unix_ms(&self) -> u64 {
        self.0.load(Ordering::SeqCst)
    }
}

#[test]
fn guard_accepts_a_live_lease_and_rejects_it_after_expiry() {
    let clock = ManualClock::new(1_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), clock.clone()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let lease = broker
        .leases()
        .grant(&scope, "agent-a", Duration::from_millis(1_000))
        .expect("grant");
    let guard = LeaseGuard::new(Arc::new(broker.leases().clone()), &lease);

    assert!(guard.check().is_ok(), "a fresh lease must authorise");

    clock.advance(1_001);
    let denied = guard.check();
    assert!(denied.is_err(), "an expired lease must not authorise");
    assert!(
        matches!(
            denied,
            Err(BrokerError::State(
                substrate_browser::BrowserError::LeaseUnusable { .. }
            ))
        ),
        "expiry must be reported as an unusable lease, got {denied:?}"
    );
}

#[test]
fn guard_rejects_a_revoked_lease() {
    let clock = ManualClock::new(2_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), clock).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let lease = broker
        .leases()
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .expect("grant");
    let guard = LeaseGuard::new(Arc::new(broker.leases().clone()), &lease);
    broker.leases().revoke(&lease.id).expect("revoke");

    assert!(
        guard.check().is_err(),
        "a cloned handle must not outlive revocation"
    );
}

#[tokio::test]
async fn broker_refuses_an_unknown_lease_and_reports_no_sessions() {
    let clock = ManualClock::new(3_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), clock).expect("broker");

    assert!(matches!(
        broker.authorize("lease-nope").await,
        Err(BrokerError::NoSession(_))
    ));
    assert!(broker.live().await.is_empty());
    assert_eq!(broker.reap_expired().await, 0);
}

#[tokio::test]
async fn a_second_broker_instance_cannot_launch_while_the_lease_is_live() {
    let clock = ManualClock::new(4_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let first = Broker::with_clock(dir.path(), clock.clone()).expect("first broker");
    let second = Broker::with_clock(dir.path(), clock.clone()).expect("second broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    // Process A holds the profile through the shared on-disk authority.
    let held = first
        .leases()
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .expect("grant");

    let attempt = second
        .acquire(&scope, "agent-b", Duration::from_secs(60))
        .await;
    assert!(
        matches!(attempt, Err(BrokerError::State(_))),
        "a live lease in another broker must fail closed, got {attempt:?}"
    );
    assert!(
        second.live().await.is_empty(),
        "a refused acquire must not publish a session"
    );

    // Once the lease expires on the shared clock the profile is free again.
    clock.advance(60_001);
    assert!(
        first
            .leases()
            .validate(&held.id, held.fencing_token)
            .is_err(),
        "the old lease must be unusable after expiry"
    );
    assert!(
        second
            .leases()
            .grant(&scope, "agent-b", Duration::from_secs(60))
            .is_ok(),
        "expiry must free the profile for a new holder"
    );
}

fn has_browser() -> bool {
    substrate_browser_broker::browser_available()
}

// The tests below launch a real (headless) browser to prove the lifecycle
// order. They take no screenshots and never touch a desktop. On a host without
// a Chrome-family binary they report the skip instead of passing silently
// (names end in `_when_a_browser_is_available` so the skip is legible).

#[tokio::test]
async fn released_handles_lose_control_when_a_browser_is_available() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let clock = ManualClock::new(5_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), clock).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let acquired = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire");
    let generation = acquired.generation;
    let lease = acquired.lease.clone();

    // A clone kept by the caller must be usable while the lease is live.
    let kept = acquired.browser.clone();
    assert!(kept.pid().await.expect("live handle").is_some());

    broker.release(acquired).await.expect("release");

    // After release the clone retains nothing: the lease is revoked
    // (`State`) and the provider slot is empty (`Released`). Either way it must
    // never report or lock a live browser again.
    match kept.pid().await {
        Err(BrokerError::Released { .. } | BrokerError::State(_)) => {},
        other => panic!("a released clone must not report a live browser, got {other:?}"),
    }
    match kept.screenshot().await {
        Err(BrokerError::Released { .. } | BrokerError::State(_)) => {},
        Ok(_) => panic!("a released clone must not act on the browser"),
        Err(other) => panic!("unexpected action error: {other:?}"),
    }
    assert!(
        broker
            .leases()
            .validate(&lease.id, lease.fencing_token)
            .is_err(),
        "release must revoke the lease"
    );
    assert!(broker.live().await.is_empty(), "release must unpublish");

    // The generation is sealed only after the browser stopped.
    let sealed = broker
        .profiles()
        .generations("alice", "work")
        .expect("generations")
        .into_iter()
        .find(|entry| entry.id == generation)
        .expect("generation recorded");
    assert!(sealed.sealed, "the browser must stop before the seal");

    // The profile is free again once the old browser is gone. Note: `ensure`
    // reuses the active generation, so this checks exclusivity, not generation
    // rotation.
    let next = broker
        .acquire(&scope, "agent-b", Duration::from_secs(120))
        .await
        .expect("next holder");
    assert_eq!(broker.live().await.len(), 1, "only the new holder is live");
    broker.release(next).await.expect("release next");
}

#[tokio::test]
async fn a_live_profile_is_refused_in_process_when_a_browser_is_available() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let held = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire");

    // Same principal/profile, still live: the broker must refuse rather than
    // launch a second browser onto the same user data directory.
    let second = broker
        .acquire(&scope, "agent-b", Duration::from_secs(120))
        .await;
    assert!(
        matches!(second, Err(BrokerError::ProfileBusy { .. })),
        "a live profile must not be reissued in-process, got {second:?}"
    );
    assert_eq!(broker.live().await.len(), 1);

    broker.release(held).await.expect("release");
}

#[tokio::test]
async fn expiry_blocks_actions_without_a_browser() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let clock = ManualClock::new(6_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), clock.clone()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let acquired = broker
        .acquire(&scope, "agent-a", Duration::from_secs(1))
        .await
        .expect("acquire");
    let handle = acquired.browser.clone();

    // Advance past the 1s TTL: the lease becomes unusable on the shared clock.
    clock.advance(1_001);

    // The action must be refused by lease re-validation before it ever touches
    // the (possibly absent) browser.
    let result = handle.screenshot().await;
    assert!(
        result.is_err(),
        "an expired lease must block screenshot, got {result:?}"
    );
    match result {
        Err(BrokerError::State(_) | BrokerError::Released { .. }) => {},
        Ok(_) => panic!("an expired lease must never allow an action"),
        Err(other) => panic!("unexpected action error: {other:?}"),
    }

    let _ = broker.release(acquired).await;
}

#[tokio::test]
async fn reap_expired_unpublishes_after_expiry() {
    if !has_browser() {
        eprintln!("skipping: no browser");
        return;
    }

    let clock = ManualClock::new(7_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), clock.clone()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let acquired = broker
        .acquire(&scope, "agent-a", Duration::from_secs(1))
        .await
        .expect("acquire");

    clock.advance(1_001);

    let reaped = broker.reap_expired().await;
    assert!(
        reaped >= 1,
        "expected at least one reaped session, got {reaped}"
    );
    assert!(
        broker.live().await.is_empty(),
        "live() must be empty after reaping expired sessions"
    );

    let _ = broker.release(acquired).await;
}

/// Fence that lets the first command through, then winds the clock past the
/// lease TTL before delegating. This is the wall-clock expiry case made
/// deterministic: the lease is valid when the action starts and dead by the
/// time the action's second command is issued.
struct ExpiringFence {
    clock: Arc<ManualClock>,
    advance_ms: u64,
    checks: AtomicU64,
    inner: LeaseGuard,
}

impl substrate_browser_cdp::FenceCheck for ExpiringFence {
    fn check(&self) -> Result<(), String> {
        let seen = self.checks.fetch_add(1, Ordering::SeqCst);
        if seen >= 1 {
            self.clock.advance(self.advance_ms);
        }
        substrate_browser_cdp::FenceCheck::check(&self.inner)
    }
}

async fn serve_fixture(html: &'static str) -> std::net::SocketAddr {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind");
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
                    html.len(),
                    html
                );
                let _ = socket.write_all(response.as_bytes()).await;
                let _ = socket.shutdown().await;
            });
        }
    });
    addr
}

#[tokio::test]
async fn a_lease_that_expires_mid_action_stops_the_action() {
    if !substrate_browser_broker::browser_available() {
        eprintln!("skipping: no browser");
        return;
    }

    let clock = ManualClock::new(9_000_000);
    let dir = tempfile::tempdir().expect("tempdir");
    // Same pieces the broker wires: a clocked lease manager, a real browser, and
    // the lease guard installed as the transport fence.
    let leases = Arc::new(
        substrate_browser::LeaseManager::with_clock(dir.path().join("leases"), clock.clone())
            .expect("lease store"),
    );
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let lease = leases
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .expect("grant");

    let addr = serve_fixture(
        "<html><head><title>Mid</title></head><body>\
         <button onclick=\"document.title='clicked'\">Go</button></body></html>",
    )
    .await;

    let mut provider = substrate_browser_cdp::CdpProvider::launch(dir.path().join("browser"), true)
        .await
        .expect("launch");
    provider
        .open(&format!("http://{addr}/"))
        .await
        .expect("open");

    let fence = Arc::new(ExpiringFence {
        clock: clock.clone(),
        advance_ms: 61_000,
        checks: AtomicU64::new(0),
        inner: LeaseGuard::new(leases.clone(), &lease),
    });

    // A single-command action is authorised: only the first check happens and
    // the lease is still valid at that instant.
    provider.set_fence(Some(fence.clone()));
    assert_eq!(
        provider
            .eval("1+1")
            .await
            .expect("first command authorised"),
        serde_json::json!(2)
    );

    // `click` needs two commands. The clock jumps past the TTL between them, so
    // the second command must be refused.
    fence.checks.store(0, Ordering::SeqCst);
    let snapshot = provider.snapshot().await.expect("snapshot");
    let reference = snapshot
        .elements
        .iter()
        .find_map(|node| node.element_ref.clone())
        .expect("an actionable element");

    fence.checks.store(0, Ordering::SeqCst);
    let outcome = provider.click(&reference).await;
    assert!(
        outcome.is_err(),
        "the action must not complete once the lease expired between its commands"
    );

    // And the title did not change, so the click genuinely did not land.
    provider.set_fence(None);
    assert_eq!(
        provider.title().await.expect("title"),
        "Mid",
        "a refused action must not have side effects"
    );

    let _ = provider.close().await;
}
