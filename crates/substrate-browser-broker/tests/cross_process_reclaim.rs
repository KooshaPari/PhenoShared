//! Cross-process reclaim: a SIGKILLed holder's lease must be reclaimed by a
//! fresh process, leaving the profile acquirable.
//!
//! The in-process tests prove `reap_dead` clears a dead `owner_pid` when the
//! record was written by the same process. That is not the property the broker
//! relies on. The real failure mode is a broker that crashes -- or is killed --
//! while holding the lease: its record survives on disk, nobody runs a drop
//! handler, and a *different* process must be able to take the profile over.
//!
//! This test drives that end to end:
//!
//! 1. spawn `examples/reclaim_holder`, which grants the lease and blocks;
//! 2. confirm the profile is blocked while the holder is alive;
//! 3. `kill -9` it and reap the zombie, so the pid is genuinely gone;
//! 4. confirm the lease file is still on disk with an unexpired TTL;
//! 5. in this process, open a fresh authority on the same root, reap, and take
//!    the profile with a strictly higher fencing token.
//!
//! No browser, network, or GUI is involved.

use std::{
    io::{BufRead, BufReader, Read},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{mpsc, Arc},
    time::{Duration, Instant},
};

use substrate_browser::{LeaseManager, ProfileStore, Scope};

const PRINCIPAL: &str = "alice";
const PROFILE: &str = "work";
/// Long enough that expiry can never be the reaping mechanism under test.
const TTL_MS: u64 = 300_000;
const WAIT_BUDGET: Duration = Duration::from_secs(5);
const POLL_STEP: Duration = Duration::from_millis(25);

/// What the holder printed on its single JSON line.
struct HolderLine {
    lease: String,
    fence: u64,
    pid: u32,
    lease_file: PathBuf,
}

impl HolderLine {
    fn parse(line: &str) -> Self {
        let value: serde_json::Value =
            serde_json::from_str(line).unwrap_or_else(|e| panic!("bad holder JSON {line:?}: {e}"));
        Self {
            lease: value["lease"]
                .as_str()
                .expect("lease id in holder JSON")
                .to_string(),
            fence: value["fence"].as_u64().expect("fence in holder JSON"),
            pid: u32::try_from(value["pid"].as_u64().expect("pid in holder JSON"))
                .expect("pid fits u32"),
            lease_file: PathBuf::from(
                value["lease_file"]
                    .as_str()
                    .expect("lease_file in holder JSON"),
            ),
        }
    }
}

/// Kills the child on drop so a failing assertion cannot leak a live holder.
struct Holder {
    child: Child,
    reaped: bool,
}

impl Drop for Holder {
    fn drop(&mut self) {
        if !self.reaped {
            let _ = Command::new("kill")
                .arg("-9")
                .arg(self.child.id().to_string())
                .status();
            let _ = self.child.wait();
        }
    }
}

/// Workspace-aware path to the example binary.
///
/// `CARGO_MANIFEST_DIR` points at the crate, while the workspace shares one
/// `target/` at the repository root, so walk up looking for it. `CARGO_TARGET_DIR`
/// and a sibling `target/` are both honoured. If nothing is built yet, build it.
fn example_binary() -> PathBuf {
    let name = format!("reclaim_holder{}", std::env::consts::EXE_SUFFIX);
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

    let mut roots: Vec<PathBuf> = Vec::new();
    if let Ok(dir) = std::env::var("CARGO_TARGET_DIR") {
        roots.push(PathBuf::from(dir));
    }
    let mut cursor: Option<&Path> = Some(&manifest);
    while let Some(dir) = cursor {
        roots.push(dir.join("target"));
        cursor = dir.parent();
    }

    let candidates: Vec<PathBuf> = roots
        .into_iter()
        .flat_map(|target| {
            [
                target.join("debug").join("examples").join(&name),
                target.join("examples").join(&name),
            ]
        })
        .collect();

    if let Some(found) = candidates.iter().find(|path| path.is_file()) {
        return found.clone();
    }

    // Not built yet: build it through the same cargo that is running this test.
    let cargo = std::env::var("CARGO").unwrap_or_else(|_| "cargo".to_string());
    let status = Command::new(cargo)
        .current_dir(&manifest)
        .args([
            "build",
            "-p",
            "substrate-browser-broker",
            "--example",
            "reclaim_holder",
        ])
        .status()
        .expect("run cargo build for the reclaim_holder example");
    assert!(status.success(), "building reclaim_holder failed: {status}");

    candidates
        .into_iter()
        .find(|path| path.is_file())
        .expect("reclaim_holder binary after a successful build")
}

/// Read the holder's single JSON line, bounded by `WAIT_BUDGET`.
fn read_holder_line(child: &mut Child) -> HolderLine {
    let stdout = child.stdout.take().expect("piped holder stdout");
    let (tx, rx) = mpsc::channel::<Option<String>>();
    std::thread::spawn(move || {
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();
        let sent = match reader.read_line(&mut line) {
            Ok(0) | Err(_) => None,
            Ok(_) => Some(line),
        };
        let _ = tx.send(sent);
    });

    let deadline = Instant::now() + WAIT_BUDGET;
    loop {
        match rx.recv_timeout(POLL_STEP) {
            Ok(Some(line)) => return HolderLine::parse(line.trim()),
            Ok(None) => panic!("holder exited before printing its lease line"),
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                panic!("holder stdout closed before printing its lease line")
            },
            Err(mpsc::RecvTimeoutError::Timeout) if Instant::now() >= deadline => {
                panic!("holder did not print its lease line within {WAIT_BUDGET:?}")
            },
            Err(mpsc::RecvTimeoutError::Timeout) => {},
        }
    }
}

/// Milliseconds since the Unix epoch, for TTL assertions.
fn now_unix_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
        .unwrap_or(0)
}

/// `kill -0`: true while the pid names a live (non-zombie) process.
fn signal_zero_alive(pid: u32) -> bool {
    Command::new("kill")
        .arg("-0")
        .arg(pid.to_string())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

/// Drain any stderr the holder produced, for a useful failure message.
fn drain_stderr(child: &mut Child) -> String {
    let mut buf = String::new();
    if let Some(mut err) = child.stderr.take() {
        let _ = err.read_to_string(&mut buf);
    }
    buf
}

#[test]
fn killed_holder_lease_is_reclaimed_by_a_fresh_process() {
    let dir = tempfile::tempdir().expect("tempdir");
    let root = dir.path().to_path_buf();
    let binary = example_binary();
    eprintln!("holder binary: {}", binary.display());

    let child = Command::new(&binary)
        .arg(&root)
        .arg(PRINCIPAL)
        .arg(PROFILE)
        .arg(TTL_MS.to_string())
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn reclaim_holder");
    let holder_pid = child.id();
    let mut holder = Holder {
        child,
        reaped: false,
    };

    let held = read_holder_line(&mut holder.child);
    assert_eq!(
        held.pid, holder_pid,
        "the holder must record its own pid, not a parent proxy"
    );
    eprintln!(
        "holder pid {} holds lease {} fence {} at {}",
        held.pid,
        held.lease,
        held.fence,
        held.lease_file.display()
    );

    // While the holder lives, the profile is genuinely blocked.
    let me = LeaseManager::new(root.join("leases")).expect("lease store");
    let scope = Scope::new(PRINCIPAL, PROFILE, "reclaimer").expect("scope");
    let blocked = me.grant(&scope, "intruder", Duration::from_millis(TTL_MS));
    assert!(
        matches!(blocked, Err(substrate_browser::BrowserError::Refused(_))),
        "a live holder must block a second grant, got {blocked:?}"
    );

    let held_on_disk = me
        .list()
        .expect("list leases")
        .into_iter()
        .find(|lease| lease.id == held.lease)
        .expect("the holder's lease record exists on disk");
    assert_eq!(held_on_disk.owner_pid, holder_pid, "owner_pid is the child");
    assert!(
        held_on_disk.remaining_ms(now_unix_ms()) > 0,
        "the lease must still be unexpired, so reaping cannot be TTL expiry"
    );
    assert!(held.lease_file.is_file(), "lease file exists while held");
    assert!(
        signal_zero_alive(holder_pid),
        "holder must be alive before the kill"
    );

    // SIGKILL: no drop handler, no cleanup, no release call.
    let killed = Command::new("kill")
        .arg("-9")
        .arg(holder_pid.to_string())
        .status()
        .expect("run kill -9");
    assert!(killed.success(), "kill -9 must succeed: {killed}");
    let status = holder.child.wait().expect("wait for killed holder");
    holder.reaped = true;
    let stderr = drain_stderr(&mut holder.child);
    assert!(
        !status.success(),
        "the holder must not have exited cleanly: {status}{stderr}"
    );

    // The pid is now genuinely gone (reaped, so not a zombie answering kill -0).
    let gone_deadline = Instant::now() + WAIT_BUDGET;
    while signal_zero_alive(holder_pid) && Instant::now() < gone_deadline {
        std::thread::sleep(POLL_STEP);
    }
    assert!(
        !signal_zero_alive(holder_pid),
        "pid {holder_pid} still answers kill -0 after SIGKILL + wait"
    );

    // The lease record outlived its owner: this is the leak being reclaimed.
    assert!(
        held.lease_file.is_file(),
        "SIGKILL must leave the lease file behind: {}",
        held.lease_file.display()
    );
    assert!(
        me.active_for(PRINCIPAL, PROFILE)
            .expect("active_for")
            .is_some(),
        "the stale record still claims the profile before reaping"
    );
    let still_blocked = me.grant(&scope, "intruder-2", Duration::from_millis(TTL_MS));
    assert!(
        matches!(
            still_blocked,
            Err(substrate_browser::BrowserError::Refused(_))
        ),
        "before reaping, the dead holder's record still blocks the profile"
    );

    // A FRESH authority over the same root must reclaim it.
    let fresh = LeaseManager::new(root.join("leases")).expect("fresh lease store");
    let reaped = fresh.reap_dead().expect("reap_dead");
    assert_eq!(reaped, 1, "exactly the dead holder's lease is reaped");
    assert!(
        !held.lease_file.exists(),
        "the stale lease file must be gone after reaping"
    );
    assert!(
        fresh
            .list()
            .expect("list leases")
            .iter()
            .all(|lease| lease.id != held.lease),
        "the stale lease must not appear in the fresh authority's listing"
    );

    // And the profile is now acquirable, with a strictly later fence.
    let taken = fresh
        .grant(&scope, "reclaimer", Duration::from_millis(TTL_MS))
        .expect("a fresh process must acquire the profile after reaping");
    assert_eq!(
        taken.owner_pid,
        std::process::id(),
        "the new lease belongs to this process"
    );
    assert!(
        taken.fencing_token > held.fence,
        "fencing tokens must advance across processes: old {} new {}",
        held.fence,
        taken.fencing_token
    );
    let validated = fresh
        .validate(&taken.id, taken.fencing_token)
        .expect("the reclaiming lease validates");
    assert_eq!(validated.id, taken.id);

    // The stale holder cannot resume: its fence is superseded.
    let stale_resume = fresh.validate(&held.lease, held.fence);
    assert!(
        stale_resume.is_err(),
        "the killed holder's token must stay invalid after reclaim"
    );

    // Profile bookkeeping is usable under the new authority, not wedged behind
    // the dead holder's record.
    let store = ProfileStore::with_gate(root.clone(), Arc::new(fresh.clone())).expect("store");
    let generation = store
        .ensure(PRINCIPAL, PROFILE)
        .expect("profile is usable once the dead lease is reclaimed");
    assert!(generation >= 1, "profile generation: {generation}");

    eprintln!(
        "reclaimed: old lease {} (fence {}) gone; new lease {} (fence {}) held by pid {}",
        held.lease, held.fence, taken.id, taken.fencing_token, taken.owner_pid
    );
}
