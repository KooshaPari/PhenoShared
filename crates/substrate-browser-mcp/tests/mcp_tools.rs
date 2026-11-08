//! Tool-layer tests for the browser-broker MCP bridge.
//!
//! These exercise the library directly: no MCP transport, no network, and no
//! browser. Acquiring a *browser* needs a Chrome-family binary, so the tests
//! drive the same authority the acquire path uses: the on-disk `LeaseManager`.
//! That is where the fencing token is enforced, and it is what the MCP layer
//! must never bypass.

use std::{
    sync::{Arc, Mutex},
    time::Duration,
};

use substrate_browser::{Clock, Scope};
use substrate_browser_broker::BrokerError;
use substrate_browser_mcp::{kind_of, AcquireParams, BrokerTools};

/// Controllable clock so TTL expiry is observable without sleeping.
#[derive(Debug, Clone, Default)]
struct ManualClock(Arc<Mutex<u64>>);

impl ManualClock {
    fn new(now: u64) -> Self {
        Self(Arc::new(Mutex::new(now)))
    }

    fn advance(&self, ms: u64) {
        let mut now = self.0.lock().unwrap();
        *now = now.saturating_add(ms);
    }
}

impl Clock for ManualClock {
    fn now_unix_ms(&self) -> u64 {
        *self.0.lock().unwrap()
    }
}

fn tools(root: &std::path::Path) -> BrokerTools {
    BrokerTools::open(root).expect("open broker tools")
}

fn scope(principal: &str, profile: &str) -> Scope {
    Scope::new(principal, profile, "test-session").expect("valid scope")
}

/// Grant a lease the way `acquire` does at the authority layer.
fn grant(
    tools: &BrokerTools,
    principal: &str,
    profile: &str,
    ttl_ms: u64,
) -> substrate_browser::Lease {
    tools
        .broker()
        .leases()
        .grant(
            &scope(principal, profile),
            "test-holder",
            Duration::from_millis(ttl_ms),
        )
        .expect("grant lease")
}

#[tokio::test]
async fn acquire_then_release_happy_path() {
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());

    // Acquire's authority step: the lease grant that carries the fencing token.
    let lease = grant(&tools, "agent-a", "work", 60_000);
    let status = tools.status().await.expect("status");
    assert_eq!(status.active_leases.len(), 1);
    assert_eq!(status.active_leases[0].fencing_token, lease.fencing_token);
    assert!(!status.active_leases[0].expired);

    let outcome = tools
        .release(&lease.id, lease.fencing_token)
        .await
        .expect("release with the current token");

    assert!(outcome.released);
    assert_eq!(outcome.lease_id, lease.id);
    // No local browser handle: the lease record is revoked, nothing invented.
    assert!(outcome.teardown.contains("lease record revoked"));

    let status = tools.status().await.expect("status after release");
    assert!(
        status.active_leases.is_empty(),
        "release must remove the lease record"
    );
}

#[tokio::test]
async fn stale_fencing_token_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());
    let lease = grant(&tools, "agent-a", "work", 60_000);
    assert!(lease.fencing_token >= 1);

    let err = tools
        .release(&lease.id, lease.fencing_token.saturating_sub(1))
        .await
        .expect_err("a stale token must be refused");

    assert!(matches!(
        err,
        BrokerError::State(substrate_browser::BrowserError::StaleFence { .. })
    ));
    assert_eq!(kind_of(&err), "StaleFence");

    // Fail-closed: the lease is untouched and still usable with the real token.
    let still_active = tools
        .broker()
        .leases()
        .active_for("agent-a", "work")
        .expect("read leases")
        .expect("lease must still exist");
    assert_eq!(still_active.id, lease.id);

    tools
        .release(&lease.id, lease.fencing_token)
        .await
        .expect("the real token still releases");
}

#[tokio::test]
async fn release_of_a_revoked_and_superseded_lease_is_refused() {
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());

    let old = grant(&tools, "agent-a", "work", 60_000);
    tools.broker().leases().revoke(&old.id).expect("revoke");
    let new = grant(&tools, "agent-a", "work", 60_000);
    assert!(new.fencing_token > old.fencing_token);

    // The old record is gone: a stale holder cannot resurrect it.
    let err = tools
        .release(&old.id, old.fencing_token)
        .await
        .expect_err("revoked lease must be refused");
    assert_eq!(kind_of(&err), "UnknownLease");

    // And it cannot tear down the newer holder either.
    let err = tools
        .release(&new.id, old.fencing_token)
        .await
        .expect_err("old token must not release the new lease");
    assert_eq!(kind_of(&err), "StaleFence");
    assert!(tools
        .broker()
        .leases()
        .active_for("agent-a", "work")
        .unwrap()
        .is_some());
}

#[tokio::test]
async fn purge_refuses_while_the_profile_is_leased() {
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());

    // Materialise the profile so there is really something to delete.
    tools
        .broker()
        .profiles()
        .ensure("agent-a", "work")
        .expect("create profile");
    let profile_dir = tools.broker().profiles().profile_dir("agent-a", "work");
    assert!(profile_dir.exists());

    let lease = grant(&tools, "agent-a", "work", 60_000);

    let err = tools
        .purge("agent-a", "work", true)
        .await
        .expect_err("purge must refuse while a live lease exists");
    assert_eq!(kind_of(&err), "Refused");
    assert!(err.to_string().contains("leased"));
    assert!(profile_dir.exists(), "refused purge must delete nothing");

    // Without confirmation it is refused too, even after the lease is gone.
    tools
        .release(&lease.id, lease.fencing_token)
        .await
        .expect("release");
    let err = tools
        .purge("agent-a", "work", false)
        .await
        .expect_err("purge needs confirm: true");
    assert_eq!(kind_of(&err), "Refused");

    let outcome = tools
        .purge("agent-a", "work", true)
        .await
        .expect("confirmed purge of an unleased profile");
    assert!(outcome.purged && outcome.existed);
    assert!(!profile_dir.exists());
}

#[tokio::test]
async fn purge_of_a_missing_profile_reports_nothing_removed() {
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());
    let outcome = tools
        .purge("nobody", "nothing", true)
        .await
        .expect("purge is a no-op for a missing profile");
    assert!(!outcome.purged);
    assert!(!outcome.existed);
}

#[tokio::test]
async fn reap_reports_counts_and_sweeps_expired_leases() {
    let dir = tempfile::tempdir().unwrap();
    let clock = ManualClock::new(1_000_000);
    let tools = BrokerTools::with_clock(dir.path(), Arc::new(clock.clone())).expect("open");

    // Nothing to reap yet: counts are still reported.
    let first = tools.reap().await.expect("reap");
    assert_eq!(first.reaped, 0);
    assert_eq!(first.leases_reaped, 0);
    assert_eq!(first.live_sessions_after, 0);

    grant(&tools, "agent-a", "work", 1_000);
    clock.advance(1_001);

    let second = tools.reap().await.expect("reap expired");
    assert_eq!(second.leases_reaped, 1, "the expired lease is swept");
    assert_eq!(second.reaped, 0, "no browser sessions in this process");
    assert!(tools
        .broker()
        .leases()
        .active_for("agent-a", "work")
        .unwrap()
        .is_none());
}

#[tokio::test]
async fn acquire_rejects_a_zero_ttl_without_launching() {
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());
    let err = tools
        .acquire(AcquireParams {
            principal: "agent-a".into(),
            profile: "work".into(),
            session: None,
            holder: None,
            ttl_ms: Some(0),
        })
        .await
        .expect_err("ttl_ms must be positive");
    assert_eq!(kind_of(&err), "Refused");
}

/// Real acquire/release, only when a Chrome-family binary is actually present.
#[tokio::test]
async fn acquire_and_release_with_a_real_browser() {
    if !substrate_browser_broker::browser_available() {
        eprintln!("skipping: no Chrome-family binary available");
        return;
    }
    let dir = tempfile::tempdir().unwrap();
    let tools = tools(dir.path());

    let info = tools
        .acquire(AcquireParams {
            principal: "agent-a".into(),
            profile: "work".into(),
            session: Some("test".into()),
            holder: Some("mcp-test".into()),
            ttl_ms: Some(60_000),
        })
        .await
        .expect("acquire with a real browser");
    assert_eq!(info.generation, 1);

    let live = tools.live().await;
    assert_eq!(live.len(), 1);
    assert_eq!(live[0].lease_id, info.lease_id);

    let outcome = tools
        .release(&info.lease_id, info.fencing_token)
        .await
        .expect("release");
    assert!(outcome.released);
    assert!(outcome.teardown.contains("browser closed"));
    assert!(tools.live().await.is_empty());
}
