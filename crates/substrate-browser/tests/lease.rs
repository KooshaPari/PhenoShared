//! Behavioural tests for the lease authority.

use std::{
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Duration,
};

use substrate_browser::{BrowserError, Clock, LeaseGate, LeaseManager, Scope};

/// Clock the test moves by hand, so expiry is deterministic.
#[derive(Debug, Default)]
struct ManualClock(AtomicU64);

impl ManualClock {
    fn advance(&self, ms: u64) {
        self.0.fetch_add(ms, Ordering::SeqCst);
    }
}

impl Clock for ManualClock {
    fn now_unix_ms(&self) -> u64 {
        1_000_000 + self.0.load(Ordering::SeqCst)
    }
}

fn manager() -> (tempfile::TempDir, Arc<ManualClock>, LeaseManager) {
    let dir = tempfile::tempdir().expect("tempdir");
    let clock = Arc::new(ManualClock::default());
    let leases =
        LeaseManager::with_clock(dir.path().join("leases"), clock.clone()).expect("lease store");
    (dir, clock, leases)
}

#[test]
fn grant_then_active_for() {
    let (_dir, _clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let lease = leases
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .expect("grant");

    assert_eq!(lease.fencing_token, 1);
    assert_eq!(lease.session, "s1");
    let active = leases.active_for("alice", "work").unwrap().expect("held");
    assert_eq!(active.id, lease.id);
    assert!(leases.has_active_lease("alice", "work").unwrap());
}

#[test]
fn second_grant_on_same_profile_is_refused() {
    let (_dir, _clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    leases
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .unwrap();

    let other_session = Scope::new("alice", "work", "s2").unwrap();
    let err = leases
        .grant(&other_session, "agent-b", Duration::from_secs(60))
        .unwrap_err();
    match err {
        BrowserError::Refused(message) => assert!(message.contains("already leased")),
        other => panic!("expected refusal, got {other:?}"),
    }
}

#[test]
fn different_profiles_are_independent() {
    let (_dir, _clock, leases) = manager();
    let a = Scope::new("alice", "work", "s1").unwrap();
    let b = Scope::new("alice", "personal", "s1").unwrap();
    leases
        .grant(&a, "agent-a", Duration::from_secs(60))
        .unwrap();
    leases
        .grant(&b, "agent-b", Duration::from_secs(60))
        .unwrap();
    assert_eq!(leases.list().unwrap().len(), 2);
}

#[test]
fn renew_extends_expiry() {
    let (_dir, clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let lease = leases
        .grant(&scope, "agent-a", Duration::from_secs(10))
        .unwrap();

    clock.advance(8_000);
    let renewed = leases.renew(&lease.id, Duration::from_secs(10)).unwrap();
    assert_eq!(renewed.issued_at_unix_ms, lease.issued_at_unix_ms);
    assert!(renewed.expires_at_unix_ms > lease.expires_at_unix_ms);
    leases.validate(&lease.id, lease.fencing_token).unwrap();
}

#[test]
fn expired_lease_is_unusable_and_reaped() {
    let (_dir, clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let lease = leases
        .grant(&scope, "agent-a", Duration::from_secs(5))
        .unwrap();

    clock.advance(6_000);
    assert!(leases.active_for("alice", "work").unwrap().is_none());
    assert!(matches!(
        leases.validate(&lease.id, lease.fencing_token),
        Err(BrowserError::LeaseUnusable { .. })
    ));
    assert!(matches!(
        leases.renew(&lease.id, Duration::from_secs(5)),
        Err(BrowserError::LeaseUnusable { .. })
    ));
    assert_eq!(leases.sweep_expired().unwrap(), 1);
    assert!(leases.list().unwrap().is_empty());
}

#[test]
fn wrong_fencing_token_is_rejected() {
    let (_dir, _clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let lease = leases
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .unwrap();

    match leases.validate(&lease.id, lease.fencing_token + 7) {
        Err(BrowserError::StaleFence { presented, .. }) => {
            assert_eq!(presented, lease.fencing_token + 7);
        },
        other => panic!("expected stale fence, got {other:?}"),
    }
}

#[test]
fn revoke_frees_the_profile_and_advances_the_fence() {
    let (_dir, _clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let first = leases
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .unwrap();
    leases.revoke(&first.id).unwrap();
    assert!(leases.active_for("alice", "work").unwrap().is_none());

    let second = leases
        .grant(&scope, "agent-b", Duration::from_secs(60))
        .unwrap();
    assert_eq!(second.fencing_token, first.fencing_token + 1);
    assert!(matches!(
        leases.validate(&first.id, first.fencing_token),
        Err(BrowserError::UnknownLease(_))
    ));
    assert!(matches!(
        leases.revoke("lease-does-not-exist"),
        Err(BrowserError::UnknownLease(_))
    ));
}

#[test]
fn grant_after_expiry_advances_the_fence() {
    let (_dir, clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let first = leases
        .grant(&scope, "agent-a", Duration::from_secs(5))
        .unwrap();

    clock.advance(6_000);
    let second = leases
        .grant(&scope, "agent-b", Duration::from_secs(5))
        .unwrap();
    assert_eq!(second.fencing_token, first.fencing_token + 1);
    assert_eq!(
        leases.active_for("alice", "work").unwrap().unwrap().id,
        second.id
    );
}

#[test]
fn tab_scoped_lease_still_excludes_the_whole_profile() {
    let (_dir, _clock, leases) = manager();
    let tabbed = Scope::new("alice", "work", "s1")
        .unwrap()
        .with_tab("t1")
        .unwrap();
    leases
        .grant(&tabbed, "agent-a", Duration::from_secs(60))
        .unwrap();

    let other_tab = Scope::new("alice", "work", "s2")
        .unwrap()
        .with_tab("t2")
        .unwrap();
    assert!(leases
        .grant(&other_tab, "agent-b", Duration::from_secs(60))
        .is_err());
}

#[test]
fn reaps_leases_whose_process_is_gone() {
    let (_dir, _clock, leases) = manager();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let live = leases
        .grant(&scope, "agent-a", Duration::from_secs(600))
        .unwrap();
    assert_eq!(live.owner_pid, std::process::id());

    // A live owner must never be reaped.
    assert_eq!(leases.reap_dead().unwrap(), 0, "live owner was reaped");
    assert!(leases.validate(&live.id, live.fencing_token).is_ok());

    // Forge a lease owned by a pid that cannot exist.
    let dead_path = leases.root().join("leases").join("lease-deadbeef.json");
    std::fs::write(
        &dead_path,
        serde_json::json!({
            "id": "lease-deadbeef",
            "principal": "alice",
            "profile": "work",
            "session": "s1",
            "tab": null,
            "holder": "agent-crashed",
            "fencing_token": 999,
            "issued_at_unix_ms": 0,
            "expires_at_unix_ms": u64::MAX,
            "owner_pid": 4194303
        })
        .to_string(),
    )
    .unwrap();

    assert_eq!(leases.reap_dead().unwrap(), 1, "dead owner was not reaped");
    assert!(!dead_path.exists());
    // The live lease survived.
    assert!(leases.validate(&live.id, live.fencing_token).is_ok());
}
