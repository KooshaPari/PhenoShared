//! A lease grant must be cheap: no browser process may exist until the session
//! is actually used.
//!
//! Previously, `Broker::acquire` launched Chrome eagerly. On a loaded
//! host that made a lease grant take 15-50s, which pushed the HTTP acquire call
//! past every client timeout and made the MCP-over-HTTP path unusable. These
//! tests pin the two properties that make the deferred launch safe:
//!
//! * acquiring publishes the lease and starts **no** process, and
//! * the two invariants that used to hang off the eager launch still hold:
//!   a failed launch does not hold the profile, and a browser is never handed
//!   out under a lease that died while it was starting.

use std::{
    fs,
    path::Path,
    process::Command,
    time::{Duration, Instant},
};

use substrate_browser_broker::{Broker, Scope};

/// Every live process command line, or `None` when this host cannot report them.
fn process_command_lines() -> Option<String> {
    let output = Command::new("ps")
        .args(["-axww", "-o", "command"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&output.stdout).into_owned())
}

/// Whether any live process references `data_dir` (Chrome is launched with
/// `--user-data-dir=<data_dir>`).
fn profile_in_use(data_dir: &Path) -> Option<bool> {
    let lines = process_command_lines()?;
    let needle = data_dir.display().to_string();
    Some(lines.contains(&needle))
}

#[tokio::test]
async fn acquiring_a_lease_does_not_launch_a_browser() {
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let grant_started = Instant::now();
    let acquired = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire");
    let granted_in = grant_started.elapsed();
    eprintln!("acquire took {granted_in:?}");

    // The lease is published and authorisable immediately...
    assert!(
        broker.browser(&acquired.lease.id).await.is_ok(),
        "the session must be live and authorisable as soon as acquire returns"
    );
    assert_eq!(
        broker.live().await.len(),
        1,
        "the lease must be published before any browser exists"
    );

    // ...but nothing has been started.
    assert!(
        !acquired.browser.is_launched().await,
        "acquire must not launch a browser"
    );
    if let Some(in_use) = profile_in_use(&acquired.data_dir) {
        assert!(
            !in_use,
            "no process may reference {} right after acquire",
            acquired.data_dir.display()
        );
    }

    if substrate_browser_broker::browser_available() {
        let action_started = Instant::now();
        let title = acquired
            .browser
            .title()
            .await
            .expect("first action launches");
        eprintln!(
            "first browser action took {:?} (title {title:?})",
            action_started.elapsed()
        );

        assert!(
            acquired.browser.is_launched().await,
            "the first action must launch the browser"
        );
        assert!(
            acquired.browser.pid().await.expect("pid").is_some(),
            "a launched browser must report a process id"
        );
        if let Some(in_use) = profile_in_use(&acquired.data_dir) {
            assert!(
                in_use,
                "the browser must be running with {} after the first action",
                acquired.data_dir.display()
            );
        }
    } else {
        eprintln!("skipping launch half: no Chrome binary on this host");
    }

    broker.release(acquired).await.expect("release");
}

#[tokio::test]
async fn a_failed_launch_revokes_the_lease_and_frees_the_profile() {
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let acquired = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire");

    // Make the generation unusable without depending on Chrome's behaviour: a
    // regular file where the user data directory belongs makes launch fail in
    // `create_dir_all`, whether or not a browser is installed. The generation
    // directory may already exist, so replace whatever is there.
    if acquired.data_dir.is_dir() {
        fs::remove_dir_all(&acquired.data_dir).expect("remove generation dir");
    } else if acquired.data_dir.exists() {
        fs::remove_file(&acquired.data_dir).expect("remove generation file");
    }
    fs::create_dir_all(acquired.data_dir.parent().expect("parent")).expect("mkdir");
    fs::write(&acquired.data_dir, b"not a directory").expect("write file");

    let err = acquired
        .browser
        .title()
        .await
        .expect_err("launch against an unusable data dir must fail");
    eprintln!("launch failure: {err}");

    assert!(
        !acquired.browser.is_launched().await,
        "a failed launch must leave no browser behind"
    );

    // Invariant: a failed launch must not hold the profile. The lease record is
    // revoked rather than left to expire.
    assert!(
        broker
            .leases()
            .validate(&acquired.lease.id, acquired.lease.fencing_token)
            .is_err(),
        "the lease must be revoked after a failed launch"
    );

    // The profile is free immediately: another holder can acquire it.
    let second = broker
        .acquire(&scope, "agent-b", Duration::from_secs(120))
        .await
        .expect("the profile must be free after a failed launch");
    broker.release(second).await.expect("release");
}

/// A handle whose browser was never launched still releases cleanly.
#[tokio::test]
async fn releasing_an_unused_lease_succeeds() {
    let dir = tempfile::tempdir().expect("tempdir");
    let broker = Broker::new(dir.path()).expect("broker");
    let scope = Scope::new("alice", "work", "s1").expect("scope");

    let acquired = broker
        .acquire(&scope, "agent-a", Duration::from_secs(120))
        .await
        .expect("acquire");
    broker.release(acquired).await.expect("release");
    assert!(
        broker.live().await.is_empty(),
        "release must unpublish the session"
    );

    // And the profile is free again.
    let again = broker
        .acquire(&scope, "agent-b", Duration::from_secs(120))
        .await
        .expect("re-acquire");
    broker.release(again).await.expect("release again");
}
