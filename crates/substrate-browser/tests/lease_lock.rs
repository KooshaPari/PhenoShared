//! The lease store's cross-process lock must never block forever.
//!
//! `LeaseManager::with_lock` used to take the lock with a **blocking**
//! `flock`, which is a blocking syscall on the calling thread. These methods are
//! called from async context, so a blocking wait pins a tokio worker. Enough
//! concurrent operations against a lock held by another process can pin every
//! worker, and then the broker's HTTP task is never scheduled: the socket keeps
//! accepting connections and nothing is ever served.
//!
//! That symptom was observed on 2026-11-09 (a brokerd accepted TCP and
//! returned zero bytes to every request while a second brokerd on the same root
//! stayed healthy). It could **not** be reproduced deliberately, so the
//! starvation mechanism is plausible rather than confirmed. What these tests
//! pin down is the part that is certain: the wait is **bounded**, it degrades to
//! an error rather than a hang, and mutual exclusion is unchanged.

use std::{
    fs,
    time::{Duration, Instant},
};

use substrate_browser::{LeaseManager, Scope};

/// Hold the lease store's lock the way another process would.
struct LockHolder {
    file: fs::File,
}

impl LockHolder {
    fn acquire(root: &std::path::Path) -> Self {
        let path = root.join("leases.lock");
        let file = fs::OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .truncate(false)
            .open(&path)
            .expect("open lock file");
        fs2::FileExt::lock_exclusive(&file).expect("take exclusive lock");
        Self { file }
    }
}

impl Drop for LockHolder {
    fn drop(&mut self) {
        let _ = fs2::FileExt::unlock(&self.file);
    }
}

#[test]
fn a_contended_lock_degrades_to_an_error_instead_of_hanging() {
    let dir = tempfile::tempdir().expect("tempdir");
    let manager = LeaseManager::new(dir.path()).expect("lease manager");
    let _holder = LockHolder::acquire(dir.path());

    let scope = Scope::new("alice", "work", "s1").expect("scope");
    let started = Instant::now();
    let err = manager
        .grant(&scope, "holder-a", Duration::from_secs(30))
        .expect_err("the grant must not succeed while another holder owns the lock");
    let elapsed = started.elapsed();

    // It returned, and it said why. The exact wording is not contractual, but a
    // refusal naming the lock is far more useful than a hang or a bare IO error.
    let message = err.to_string();
    assert!(
        message.contains("lock"),
        "the error should name the lock, got: {message}"
    );

    // Bounded: it must give up well inside the lease TTL it was asked for,
    // and inside a window that proves it is not blocking indefinitely.
    assert!(
        elapsed < Duration::from_secs(20),
        "the wait must be bounded, took {elapsed:?}"
    );
    assert!(
        elapsed >= Duration::from_secs(1),
        "it should have waited for the lock before giving up, took {elapsed:?}"
    );
}

#[test]
fn mutual_exclusion_is_still_guaranteed() {
    let dir = tempfile::tempdir().expect("tempdir");
    let first = LeaseManager::new(dir.path()).expect("first manager");
    let second = LeaseManager::new(dir.path()).expect("second manager");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let lease = first
        .grant(&scope, "holder-a", Duration::from_secs(30))
        .expect("first grant succeeds");
    assert_eq!(lease.fencing_token, 1);

    // A second manager on the same root must not be able to take the same
    // profile while the first lease is live - not even from a different
    // session. The lease store enforces this itself, so the exclusivity does
    // not depend on a caller checking first.
    let other_session = Scope::new("alice", "work", "s2").expect("scope");
    let err = second
        .grant(&other_session, "holder-b", Duration::from_secs(30))
        .expect_err("the profile is already leased");
    assert!(
        err.to_string().contains("already leased"),
        "expected a refusal naming the live lease, got: {err}"
    );

    // Once the lease is revoked the profile is grantable again, and the new
    // grant must carry a strictly newer fencing token so the old token can
    // never be mistaken for the current one.
    first.revoke(&lease.id).expect("revoke");

    let next = second
        .grant(&scope, "holder-b", Duration::from_secs(30))
        .expect("grant succeeds once the profile is free");
    assert!(
        next.fencing_token > lease.fencing_token,
        "a later grant must carry a strictly newer fencing token, got {} then {}",
        lease.fencing_token,
        next.fencing_token
    );

    // The revoked token must not validate. `revoke` removes the lease record
    // outright, so the refusal is "no such lease"; if a record survives for
    // any reason the fencing comparison must catch it instead. Either way the
    // old token is dead.
    let err = first
        .validate(&lease.id, lease.fencing_token)
        .expect_err("the revoked token must be refused");
    let message = err.to_string();
    assert!(
        message.contains("no such lease") || message.contains("stale fencing token"),
        "expected the revoked lease to be refused, got: {message}"
    );
}

#[test]
fn a_released_lock_is_reacquired_without_delay() {
    let dir = tempfile::tempdir().expect("tempdir");
    let manager = LeaseManager::new(dir.path()).expect("lease manager");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    {
        let _holder = LockHolder::acquire(dir.path());
        assert!(manager
            .grant(&scope, "blocked", Duration::from_secs(30))
            .is_err());
    }

    // Once the holder is gone the lock must be available immediately - the
    // bounded wait must not turn into a permanent refusal.
    let started = Instant::now();
    manager
        .grant(&scope, "after-release", Duration::from_secs(30))
        .expect("grant succeeds once the lock is free");
    assert!(
        started.elapsed() < Duration::from_secs(1),
        "the lock should be taken promptly once free, took {:?}",
        started.elapsed()
    );
}
