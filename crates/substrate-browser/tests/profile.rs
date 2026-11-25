//! Behavioural tests for the profile generation store.

use std::{
    fs,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Duration,
};

use substrate_browser::{BrowserError, Clock, LeaseManager, ProfileStore, Scope};

#[derive(Debug, Default)]
struct ManualClock(AtomicU64);

impl Clock for ManualClock {
    fn now_unix_ms(&self) -> u64 {
        1_700_000_000_000 + self.0.load(Ordering::SeqCst)
    }
}

fn store() -> (tempfile::TempDir, ProfileStore) {
    let dir = tempfile::tempdir().expect("tempdir");
    let store = ProfileStore::new(dir.path().join("state")).expect("store");
    (dir, store)
}

#[test]
fn ensure_creates_generation_one_and_is_idempotent() {
    let (_dir, store) = store();
    assert_eq!(store.ensure("alice", "work").unwrap(), 1);
    assert_eq!(store.ensure("alice", "work").unwrap(), 1);
    assert_eq!(store.active("alice", "work").unwrap(), Some(1));
    assert_eq!(store.generations("alice", "work").unwrap().len(), 1);
    assert!(store.data_dir("alice", "work", 1).is_dir());
}

#[test]
fn generations_have_separate_data_directories() {
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();
    let first = store.data_dir("alice", "work", 1);
    fs::write(first.join("Cookies"), b"authenticated").unwrap();

    let second_id = store.rotate("alice", "work").unwrap();
    assert_eq!(second_id, 2);
    let second = store.data_dir("alice", "work", 2);
    assert_ne!(first, second);
    assert!(
        !second.join("Cookies").exists(),
        "a rotated generation must start empty, not inherit the previous jar"
    );
    assert_eq!(store.active("alice", "work").unwrap(), Some(2));
}

#[test]
fn fork_requires_a_sealed_source() {
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();

    match store.fork("alice", "work", 1) {
        Err(BrowserError::Refused(message)) => assert!(message.contains("not sealed")),
        other => panic!("expected refusal, got {other:?}"),
    }

    store.seal("alice", "work", 1).unwrap();
    let fork = store.fork("alice", "work", 1).unwrap();
    assert_eq!(fork, 2);

    let generations = store.generations("alice", "work").unwrap();
    let forked = generations.iter().find(|g| g.id == fork).unwrap();
    assert_eq!(forked.parent, Some(1));
    assert!(!forked.sealed);
    // Forking does not change which generation is active.
    assert_eq!(store.active("alice", "work").unwrap(), Some(1));
}

#[test]
fn fork_copies_the_data_directory() {
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();
    fs::write(store.data_dir("alice", "work", 1).join("Local State"), b"x").unwrap();
    store.seal("alice", "work", 1).unwrap();

    let fork = store.fork("alice", "work", 1).unwrap();
    assert!(store
        .data_dir("alice", "work", fork)
        .join("Local State")
        .is_file());
}

#[test]
fn promote_is_compare_and_swap() {
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();
    let second = store.rotate("alice", "work").unwrap();

    // The caller's belief is now stale: it still thinks generation 1 is active.
    match store.promote("alice", "work", 1, Some(1)) {
        Err(BrowserError::PromotionConflict { expected, actual }) => {
            assert_eq!(expected, 1);
            assert_eq!(actual, Some(second));
        },
        other => panic!("expected conflict, got {other:?}"),
    }

    store.promote("alice", "work", 1, Some(second)).unwrap();
    assert_eq!(store.active("alice", "work").unwrap(), Some(1));
}

#[test]
fn promote_rejects_unknown_generation() {
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();
    assert!(matches!(
        store.promote("alice", "work", 99, Some(1)),
        Err(BrowserError::UnknownGeneration { generation: 99, .. })
    ));
}

#[test]
fn remove_refuses_active_and_last_generation() {
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();

    assert!(matches!(
        store.remove("alice", "work", 1),
        Err(BrowserError::Refused(_))
    ));

    let second = store.rotate("alice", "work").unwrap();
    store.promote("alice", "work", 1, Some(second)).unwrap();
    // Generation 2 is no longer active and a later one exists, so it may go.
    store.remove("alice", "work", second).unwrap();
    assert_eq!(store.generations("alice", "work").unwrap().len(), 1);
    assert!(!store.data_dir("alice", "work", second).exists());
}

#[test]
fn a_live_lease_blocks_generation_changes() {
    let dir = tempfile::tempdir().expect("tempdir");
    let clock = Arc::new(ManualClock::default());
    let leases =
        Arc::new(LeaseManager::with_clock(dir.path().join("leases"), clock).expect("lease store"));
    let store =
        ProfileStore::with_gate(dir.path().join("state"), leases.clone()).expect("gated store");

    store.ensure("alice", "work").unwrap();
    let scope = Scope::new("alice", "work", "s1").unwrap();
    let lease = leases
        .grant(&scope, "agent-a", Duration::from_secs(60))
        .unwrap();

    for outcome in [
        store.rotate("alice", "work").map(|_| ()),
        store.seal("alice", "work", 1),
        store.fork("alice", "work", 1).map(|_| ()),
        store.promote("alice", "work", 1, Some(1)),
        store.remove("alice", "work", 1),
    ] {
        assert!(matches!(outcome, Err(BrowserError::Refused(_))));
    }

    leases.revoke(&lease.id).unwrap();
    assert!(store.rotate("alice", "work").is_ok());
}

#[test]
fn active_data_dir_resolves_the_active_generation() {
    let (_dir, store) = store();
    assert!(store.active_data_dir("alice", "work").is_err());
    store.ensure("alice", "work").unwrap();
    let path = store.active_data_dir("alice", "work").unwrap();
    assert!(path.ends_with("gen-1"));

    let second = store.rotate("alice", "work").unwrap();
    let path = store.active_data_dir("alice", "work").unwrap();
    assert!(path.ends_with(format!("gen-{second}")));
}

#[cfg(unix)]
#[test]
fn profile_directories_are_owner_only() {
    use std::os::unix::fs::PermissionsExt;
    let (_dir, store) = store();
    store.ensure("alice", "work").unwrap();
    let mode = fs::metadata(store.data_dir("alice", "work", 1))
        .unwrap()
        .permissions()
        .mode()
        & 0o777;
    assert_eq!(
        mode, 0o700,
        "browser data directories must not be group/world readable"
    );
}

#[test]
fn rejects_path_traversal_in_profile_components() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().join("state");
    let store = ProfileStore::new(&root).expect("store");

    for (principal, profile) in [
        ("../escape", "work"),
        ("alice", "../../escape"),
        ("alice", ".."),
        ("alice/b", "work"),
        ("", "work"),
        ("alice", "Work"),
    ] {
        let outcome = store.ensure(principal, profile);
        assert!(
            outcome.is_err(),
            "escaping component {principal:?}/{profile:?} must be refused"
        );
    }

    // Nothing was written outside the profiles root.
    let escaped = dir.path().join("escape");
    assert!(
        !escaped.exists(),
        "a refused component must not create a directory outside the store"
    );
}

#[test]
fn concurrent_generation_creation_does_not_lose_writes() {
    use std::sync::Arc;

    let dir = tempfile::tempdir().expect("tempdir");
    let store = Arc::new(ProfileStore::new(dir.path().join("state")).expect("store"));
    store.ensure("alice", "work").expect("seed");

    let mut handles = Vec::new();
    for _ in 0..4 {
        let store = store.clone();
        handles.push(std::thread::spawn(move || {
            for _ in 0..5 {
                store.rotate("alice", "work").expect("rotate");
            }
        }));
    }
    for handle in handles {
        handle.join().expect("join");
    }

    let generations = store.generations("alice", "work").expect("generations");
    assert_eq!(
        generations.len(),
        1 + 4 * 5,
        "the manifest read-modify-write must not drop concurrent rotations"
    );
    let mut ids: Vec<u64> = generations.iter().map(|g| g.id).collect();
    ids.sort_unstable();
    ids.dedup();
    assert_eq!(
        ids.len(),
        generations.len(),
        "generation ids must be unique"
    );
}
