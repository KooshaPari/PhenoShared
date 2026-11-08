//! Proves that the broker's per-profile authority gives N independent profiles
//! on disk: two different profiles are leased at the same time, one profile is
//! never leased twice, and each profile owns a separate generation directory.
//!
//! Nothing here launches a browser, opens a socket, or needs a GUI. Isolation is
//! established by the on-disk separation of profile directories and by the
//! per-`principal/profile` fencing counter, which is what a real launch turns
//! into a separate `--user-data-dir` process. That proves *filesystem-level*
//! profile isolation only; it does not prove cookie-jar isolation inside a
//! running browser (see `docs/MULTI-PROFILE.md`).
use std::{
    fs,
    path::Path,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Duration,
};

use substrate_browser_broker::{Broker, Clock, Scope};

/// Clock the tests control, so no test sleeps and no TTL can expire by accident.
struct ManualClock(AtomicU64);

impl ManualClock {
    fn new(now_unix_ms: u64) -> Arc<Self> {
        Arc::new(Self(AtomicU64::new(now_unix_ms)))
    }
}

impl Clock for ManualClock {
    fn now_unix_ms(&self) -> u64 {
        self.0.load(Ordering::SeqCst)
    }
}

const TTL: Duration = Duration::from_secs(300);

fn broker(now_unix_ms: u64) -> (tempfile::TempDir, Broker) {
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::with_clock(dir.path(), ManualClock::new(now_unix_ms)).expect("broker");
    (dir, broker)
}

/// Different profiles of the same principal are independent: holding one must
/// not block, expire, or interfere with the other.
#[test]
fn different_profiles_are_leased_simultaneously() {
    let (_dir, broker) = broker(1_000_000);
    let work = Scope::new("alice", "work", "s1").expect("work scope");
    let personal = Scope::new("alice", "personal", "s2").expect("personal scope");

    let work_lease = broker
        .leases()
        .grant(&work, "agent-work", TTL)
        .expect("alice/work must be grantable");
    let personal_lease = broker
        .leases()
        .grant(&personal, "agent-personal", TTL)
        .expect("alice/personal must be grantable while alice/work is held");

    // Concurrency, stated as the property that matters: both leases are live at
    // the same instant and each is the active holder of its own profile.
    assert!(broker
        .leases()
        .validate(&work_lease.id, work_lease.fencing_token)
        .is_ok());
    assert!(broker
        .leases()
        .validate(&personal_lease.id, personal_lease.fencing_token)
        .is_ok());
    assert_ne!(work_lease.id, personal_lease.id, "leases must be distinct");

    let active_work = broker
        .leases()
        .active_for("alice", "work")
        .expect("active work")
        .expect("alice/work must have a holder");
    let active_personal = broker
        .leases()
        .active_for("alice", "personal")
        .expect("active personal")
        .expect("alice/personal must have a holder");
    assert_eq!(active_work.holder, "agent-work");
    assert_eq!(active_personal.holder, "agent-personal");
    assert_eq!(active_work.profile_key(), "alice/work");
    assert_eq!(active_personal.profile_key(), "alice/personal");

    // Revoking one leaves the other untouched.
    broker.leases().revoke(&work_lease.id).expect("revoke work");
    assert!(
        broker
            .leases()
            .active_for("alice", "personal")
            .expect("active personal")
            .is_some(),
        "revoking alice/work must not disturb alice/personal"
    );
}

/// Exclusivity is per profile, not per session and not per broker: the same
/// profile cannot be leased twice, while a sibling profile still can.
#[test]
fn the_same_profile_cannot_be_leased_twice() {
    let (_dir, broker) = broker(2_000_000);
    let first = Scope::new("alice", "work", "s1").expect("first scope");
    // A different session label, same principal and profile: still one jar.
    let second = Scope::new("alice", "work", "s2").expect("second scope");
    let sibling = Scope::new("alice", "personal", "s3").expect("sibling scope");

    let held = broker
        .leases()
        .grant(&first, "agent-a", TTL)
        .expect("first grant");

    let refused = broker.leases().grant(&second, "agent-b", TTL);
    let Err(err) = refused else {
        panic!("a second lease on alice/work must be refused");
    };
    assert!(
        format!("{err}").contains("alice/work"),
        "the refusal must name the profile key, got {err}"
    );

    // The refusal did not disturb the holder...
    assert_eq!(
        broker
            .leases()
            .active_for("alice", "work")
            .expect("active")
            .expect("holder")
            .id,
        held.id
    );
    // ...and it is not global: a sibling profile is still available.
    broker
        .leases()
        .grant(&sibling, "agent-c", TTL)
        .expect("a different profile must still be grantable");

    // A second broker instance over the same root sees the same authority, so
    // exclusivity is not process-local state.
    let other =
        Broker::with_clock(broker.root(), ManualClock::new(2_000_000)).expect("second broker");
    assert!(
        other.leases().grant(&first, "agent-d", TTL).is_err(),
        "a second broker over the same root must observe the live lease"
    );
}

/// Each profile resolves to its own generation directory, and a write in one is
/// not visible from the other.
#[test]
fn each_profile_owns_its_generation_directory() {
    let (_dir, broker) = broker(3_000_000);
    let store = broker.profiles();

    let work_gen = store.ensure("alice", "work").expect("ensure work");
    let personal_gen = store.ensure("alice", "personal").expect("ensure personal");

    // First use of each profile creates its own generation 1.
    assert_eq!(work_gen, 1);
    assert_eq!(personal_gen, 1);

    let work_dir = store.active_data_dir("alice", "work").expect("work dir");
    let personal_dir = store
        .active_data_dir("alice", "personal")
        .expect("personal dir");

    assert_ne!(
        work_dir, personal_dir,
        "distinct profiles must map to distinct user-data directories"
    );
    assert!(work_dir.is_dir(), "{} must exist", work_dir.display());
    assert!(
        personal_dir.is_dir(),
        "{} must exist",
        personal_dir.display()
    );

    // Both hang off <root>/profiles/alice, but only there: the divergence starts
    // at the profile segment, which is what makes them separate jars.
    let profiles_root = broker.root().join("profiles").join("alice");
    assert_eq!(
        work_dir.parent().and_then(Path::parent),
        Some(profiles_root.as_path()),
        "{} must live directly under {}",
        work_dir.display(),
        profiles_root.display()
    );
    assert_eq!(
        personal_dir.parent().and_then(Path::parent),
        Some(profiles_root.as_path())
    );
    // Both leaves are named `gen-1`: the isolation comes from the profile
    // segment, so the profile directories themselves must differ.
    assert_ne!(
        work_dir.parent(),
        personal_dir.parent(),
        "profile directories must differ even though both generations are gen-1"
    );

    // A cookie-jar stand-in written into one profile is invisible from the
    // other: no shared file, no shared directory, no copy.
    let marker = work_dir.join("cookie-jar.json");
    fs::write(
        &marker,
        br#"{"origin":"https://example.test","token":"work"}"#,
    )
    .expect("write marker");
    let mirrored = personal_dir.join("cookie-jar.json");
    assert!(
        marker.exists(),
        "the marker must exist in alice/work's data dir"
    );
    assert!(
        !mirrored.exists(),
        "alice/personal must not see alice/work's cookie jar at {}",
        mirrored.display()
    );

    // Nothing inside the sibling profile's subtree mentions the marker either.
    let leaked: Vec<_> = walk(&personal_dir)
        .into_iter()
        .filter(|path| {
            path.file_name()
                .map(|name| name == "cookie-jar.json")
                .unwrap_or(false)
        })
        .collect();
    assert!(
        leaked.is_empty(),
        "no file named cookie-jar.json may appear under {}, found {leaked:?}",
        personal_dir.display()
    );

    // Manifests are separate files in separate profile directories, so the
    // generation bookkeeping of one profile cannot be read from the other.
    let work_manifest = profiles_root.join("work").join("manifest.json");
    let personal_manifest = profiles_root.join("personal").join("manifest.json");
    assert!(
        work_manifest.is_file(),
        "{} must exist",
        work_manifest.display()
    );
    assert!(
        personal_manifest.is_file(),
        "{} must exist",
        personal_manifest.display()
    );
    assert_ne!(work_manifest, personal_manifest);
    assert_eq!(
        store.generations("alice", "work").expect("work gens").len(),
        1
    );
    assert_eq!(
        store
            .generations("alice", "personal")
            .expect("personal gens")
            .len(),
        1
    );
}

/// Fencing tokens are monotonic per `principal/profile`, so each profile starts
/// its own sequence at 1 and advancing one does not advance the other.
#[test]
fn fences_advance_independently_per_profile() {
    let (_dir, broker) = broker(4_000_000);
    let work = Scope::new("alice", "work", "s1").expect("work scope");
    let personal = Scope::new("alice", "personal", "s2").expect("personal scope");

    // Both profiles begin their own sequence at fence 1.
    let work_first = broker
        .leases()
        .grant(&work, "agent-w1", TTL)
        .expect("work 1");
    let personal_first = broker
        .leases()
        .grant(&personal, "agent-p1", TTL)
        .expect("personal 1");
    assert_eq!(
        work_first.fencing_token, 1,
        "alice/work must start at fence 1"
    );
    assert_eq!(
        personal_first.fencing_token, 1,
        "alice/personal must start its own sequence at fence 1, not continue alice/work's"
    );

    // Re-granting one profile advances only that profile's fence.
    broker.leases().revoke(&work_first.id).expect("revoke work");
    let work_second = broker
        .leases()
        .grant(&work, "agent-w2", TTL)
        .expect("work 2");
    assert_eq!(work_second.fencing_token, 2, "alice/work must advance to 2");
    assert_eq!(
        broker
            .leases()
            .active_for("alice", "personal")
            .expect("active personal")
            .expect("holder")
            .fencing_token,
        personal_first.fencing_token,
        "alice/personal's fence must not move when alice/work advances"
    );

    // The superseded work token is rejected, and the personal token still works.
    assert!(broker
        .leases()
        .validate(&work_first.id, work_first.fencing_token)
        .is_err());
    assert!(broker
        .leases()
        .validate(&personal_first.id, personal_first.fencing_token)
        .is_ok());

    // And the reverse direction holds as well.
    broker
        .leases()
        .revoke(&personal_first.id)
        .expect("revoke personal");
    let personal_second = broker
        .leases()
        .grant(&personal, "agent-p2", TTL)
        .expect("personal 2");
    assert_eq!(personal_second.fencing_token, 2);
    assert_eq!(
        broker
            .leases()
            .active_for("alice", "work")
            .expect("active work")
            .expect("holder")
            .fencing_token,
        work_second.fencing_token,
        "alice/work's fence must not move when alice/personal advances"
    );
}

/// Every regular file beneath `dir`, recursively. Only used to assert that no
/// marker file leaks between profile trees.
fn walk(dir: &Path) -> Vec<std::path::PathBuf> {
    let mut out = Vec::new();
    let Ok(entries) = fs::read_dir(dir) else {
        return out;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            out.extend(walk(&path));
        } else {
            out.push(path);
        }
    }
    out
}
