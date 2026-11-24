//! Shutdown correctness: releasing a browser must reap its whole process tree.
//!
//! The defect these tests pin down: `Child::kill` only signals the Chrome
//! parent, so renderer/GPU/utility children survived a "successful" release,
//! reparented to init, still holding a throwaway `--user-data-dir`. The promise
//! the broker makes is that it is the authority preventing orphaned browsers,
//! so these are correctness tests, not cosmetics.
//!
//! Everything here is headless and scoped to a throwaway profile in a temp dir.
//! A user's real Chrome instances must be untouched, and that is asserted too.
//!
//! The Unix half (`process group`) runs on macOS/Linux. The Windows half (`job
//! object`) is gated `#[cfg(windows)]` at the bottom of this file and is the
//! *only* place that path is ever executed: no Unix host can run it, so until
//! this landed it was compile-checked but never run. The
//! `.github/workflows/windows-browser-tree.yml` job runs exactly this file on
//! `windows-latest`.

use std::{
    path::{Path, PathBuf},
    time::Duration,
};

use substrate_browser_cdp::{chrome_binary, ChromeProcess, LaunchOptions};

#[cfg(unix)]
use substrate_browser_cdp::processes_using_user_data_dir;

/// A throwaway directory for one launch.
///
/// Work artifacts belong under `~/CodeProjects/temp`, so prefer that as the
/// temp root and fall back to the platform temp dir when it is absent.
#[cfg(unix)]
fn scratch() -> tempfile::TempDir {
    let base = std::env::var_os("HOME")
        .map(PathBuf::from)
        .map(|home| home.join("CodeProjects").join("temp"))
        .filter(|path| path.is_dir());
    let mut builder = tempfile::Builder::new();
    builder.prefix("cdp-tree.");
    match base {
        Some(base) => builder.tempdir_in(base).expect("scratch dir"),
        None => builder.tempdir().expect("scratch dir"),
    }
}

/// Poll until nothing references `profile`, or the budget expires.
#[cfg(unix)]
fn wait_until_released(profile: &Path, budget: Duration) -> Vec<u32> {
    let deadline = std::time::Instant::now() + budget;
    loop {
        let remaining = processes_using_user_data_dir(profile);
        if remaining.is_empty() || std::time::Instant::now() >= deadline {
            return remaining;
        }
        std::thread::sleep(Duration::from_millis(50));
    }
}

/// Pids whose command line runs the browser binary *but not* this launch's
/// profile directory: i.e. the user's own browsers.
#[cfg(unix)]
fn unrelated_browser_pids(binary: &Path, profile: &Path) -> Vec<u32> {
    let binary = binary.display().to_string();
    let profile = profile.display().to_string();
    let Ok(output) = std::process::Command::new("ps")
        .args(["-ww", "-eo", "pid=,args="])
        .output()
    else {
        return Vec::new();
    };
    String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| {
            let line = line.trim_start();
            let (pid, command) = line.split_once(char::is_whitespace)?;
            if !command.contains(&binary) || command.contains(&profile) {
                return None;
            }
            pid.parse::<u32>().ok()
        })
        .collect()
}

#[cfg(unix)]
#[test]
fn the_scanner_only_matches_its_own_profile() {
    // A path nothing can be using must yield no pids; this is the scoping
    // guarantee every kill decision in `process_tree` leans on.
    let phantom = Path::new("/nonexistent/phenotype-cdp-no-such-profile-xyzzy");
    assert!(processes_using_user_data_dir(phantom).is_empty());
}

#[cfg(unix)]
#[tokio::test]
async fn shutdown_reaps_the_whole_browser_tree() {
    let Ok(binary) = chrome_binary() else {
        eprintln!("skipping: no Chrome/Chromium binary found");
        return;
    };

    let temp = scratch();
    let profile = temp.path().join("profile");

    // Snapshot the user's own browsers *before* launching. They are outside the
    // launch's process group and outside its profile directory; they must all
    // survive shutdown.
    let outsiders_before = unrelated_browser_pids(&binary, &profile);

    let browser = ChromeProcess::launch(&LaunchOptions::headless(&profile))
        .await
        .expect("launch");
    assert!(
        browser.process_group().is_some(),
        "the launcher must put Chrome in its own process group; without one a \
         whole-tree shutdown is impossible"
    );

    // Chrome really is a tree here: the parent plus at least one child share
    // the unique profile path.
    let before = processes_using_user_data_dir(&profile);
    assert!(
        !before.is_empty(),
        "no process referenced {} immediately after launch",
        profile.display()
    );
    eprintln!(
        "EVIDENCE profile={} pgid={:?} processes-before-shutdown={} [{:?}]",
        profile.display(),
        browser.process_group(),
        before.len(),
        before
    );

    browser.shutdown().await.expect("shutdown");

    // Measured, not assumed: nothing may reference the throwaway profile.
    let leaked = wait_until_released(&profile, Duration::from_secs(5));
    eprintln!(
        "EVIDENCE profile={} processes-after-shutdown={} [{:?}]",
        profile.display(),
        leaked.len(),
        leaked
    );
    assert!(
        leaked.is_empty(),
        "shutdown left {} process(es) holding {}: {:?}",
        leaked.len(),
        profile.display(),
        leaked
    );

    // And the user's browsers were not touched. CI has no user session: every
    // browser in this snapshot belongs to a concurrent test and may be torn
    // down by its owner, so this check is only meaningful on a developer
    // machine.
    if std::env::var_os("CI").is_none() {
        let outsiders_after = unrelated_browser_pids(&binary, &profile);
        for pid in &outsiders_before {
            assert!(
                outsiders_after.contains(pid),
                "process {pid} outside the launch's own group disappeared during shutdown"
            );
        }
    }
}

#[cfg(unix)]
#[tokio::test]
async fn dropping_the_handle_also_reaps_the_tree() {
    let Ok(binary) = chrome_binary() else {
        eprintln!("skipping: no Chrome/Chromium binary found");
        return;
    };

    let temp = scratch();
    let profile = temp.path().join("profile");

    // Snapshot the user's own browsers *before* launching. They are outside the
    // launch's process group and outside its profile directory; they must all
    // survive the drop. CI has no user session: every browser in this snapshot
    // belongs to a concurrent test and may be torn down by its owner, so the
    // comparison below is only meaningful on a developer machine and the
    // snapshot itself is skipped there.
    let outsiders_before = if std::env::var_os("CI").is_none() {
        unrelated_browser_pids(&binary, &profile)
    } else {
        Vec::new()
    };

    let browser = ChromeProcess::launch(&LaunchOptions::headless(&profile))
        .await
        .expect("launch");
    assert!(!processes_using_user_data_dir(&profile).is_empty());
    drop(browser);

    let leaked = wait_until_released(&profile, Duration::from_secs(5));
    assert!(
        leaked.is_empty(),
        "drop orphaned {} process(es) holding {}: {:?}",
        leaked.len(),
        profile.display(),
        leaked
    );

    // And the user's browsers were not touched. The comparison is skipped on a
    // bare runner, where the pre-launch snapshot is empty by construction.
    if std::env::var_os("CI").is_none() {
        let outsiders_after = unrelated_browser_pids(&binary, &profile);
        for pid in &outsiders_before {
            assert!(
                outsiders_after.contains(pid),
                "process {pid} outside the launch's own group disappeared"
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Windows: job-object teardown
// ---------------------------------------------------------------------------
//
// The Windows equivalents of the two tests above. Until this landed the
// job-object path was type-checked but never executed, because no Unix host can
// run it; `.github/workflows/windows-browser-tree.yml` runs this file on
// `windows-latest`.
//
// Two *independent* measurements are asserted, because the job object must not
// be the only thing standing between a shutdown and a leak: the parent/child
// graph (every pid the launch created must be gone) and the unique
// `--user-data-dir` (nothing may still reference it).
//
// An unreadable process table skips before a launch and panics after one,
// because a green result must be a measurement rather than a claim.

/// Process-table access on Windows: `std` cannot read another argv there.
#[cfg(windows)]
#[path = "support/windows_process.rs"]
mod winproc;

#[cfg(windows)]
use winproc::{descendants, pids_referencing, poll_until, read_table, unrelated_browsers};

/// A throwaway directory for one launch, on Windows.
#[cfg(windows)]
fn win_scratch() -> tempfile::TempDir {
    let base = std::env::var_os("USERPROFILE")
        .map(PathBuf::from)
        .map(|home| home.join("CodeProjects").join("temp"))
        .filter(|path| path.is_dir());
    let mut builder = tempfile::Builder::new();
    builder.prefix("cdp-tree.");
    match base {
        Some(base) => builder.tempdir_in(base).expect("scratch dir"),
        None => builder.tempdir().expect("scratch dir"),
    }
}

/// The browser to drive, or a clear skip when this machine cannot be measured.
#[cfg(windows)]
fn win_guard() -> Option<PathBuf> {
    let Ok(binary) = chrome_binary() else {
        eprintln!("skipping: no Chrome/Chromium found (CHROME_BIN unset, no default install)");
        return None;
    };
    if binary.is_absolute() && !binary.is_file() {
        eprintln!(
            "skipping: the resolved browser {} does not exist",
            binary.display()
        );
        return None;
    }
    if winproc::table().is_none() {
        eprintln!(
            "skipping: could not enumerate the Windows process table \
             (Get-CimInstance Win32_Process unavailable)"
        );
        return None;
    }
    Some(binary)
}

/// One launch plus the measurements taken before it was shut down.
#[cfg(windows)]
struct Launched {
    // Taken (not moved) by the test body, so the surrounding measurements stay
    // borrowable after the handle is consumed.
    browser: Option<ChromeProcess>,
    pid: u32,
    tree: Vec<u32>,
    profile: PathBuf,
    needle: String,
    binary: String,
    outsiders: Vec<u32>,
    // Held for the launch's lifetime so the profile survives; declared last so
    // the browser and its job handle drop before the directory is removed.
    _temp: tempfile::TempDir,
}

/// Launch headless Chrome and capture the tree it created.
#[cfg(windows)]
async fn launch_tree(binary: &Path) -> Launched {
    let temp = win_scratch();
    let profile = temp.path().join("profile");
    let needle = profile.display().to_string();
    let binary_needle = binary.display().to_string();

    // Snapshot the user's own browsers *before* launching: they are outside this
    // launch's job object and must all survive shutdown.
    let outsiders = unrelated_browsers(&read_table("pre-launch"), &binary_needle, &needle);

    let browser = ChromeProcess::launch(&LaunchOptions::headless(&profile))
        .await
        .expect("launch");
    let pid = browser.pid().expect("the launched browser must have a pid");

    // Children take a moment to appear. Wait for the launch to have descendants
    // so the "before" side is a real tree, not a parent that has not forked.
    let (table, _) = poll_until(Duration::from_secs(15), |table| {
        !descendants(table, pid).is_empty()
    });
    let tree = descendants(&table, pid);
    let referencing = pids_referencing(&table, &needle);
    eprintln!(
        "EVIDENCE(before) pid={pid} descendants={} [{tree:?}] profile-refs={} [{referencing:?}]",
        tree.len(),
        referencing.len()
    );
    assert!(
        !tree.is_empty(),
        "the launched browser (pid {pid}) had no child process within 15s; there is \
         no tree to reap, so this test would prove nothing"
    );
    assert!(
        !referencing.is_empty(),
        "no process referenced {} after launch, so the launch is not identifiable \
         by its throwaway profile",
        profile.display()
    );

    Launched {
        browser: Some(browser),
        pid,
        tree,
        profile,
        needle,
        binary: binary_needle,
        outsiders,
        _temp: temp,
    }
}

/// Pids belonging to this launch that the table still shows as alive.
#[cfg(windows)]
fn survivors(table: &[winproc::WinProcess], launched: &Launched) -> Vec<u32> {
    let mut leaked = vec![launched.pid];
    leaked.extend(launched.tree.iter().copied());
    leaked.extend(pids_referencing(table, &launched.needle));
    leaked.retain(|pid| table.iter().any(|row| row.pid == *pid));
    leaked.sort_unstable();
    leaked.dedup();
    leaked
}

/// Nothing from the launch is alive and nothing references its profile.
#[cfg(windows)]
fn verify_reaped(launched: &Launched, evidence: &str) {
    let (table, clean) = poll_until(Duration::from_secs(10), |table| {
        survivors(table, launched).is_empty()
    });
    let leaked = survivors(&table, launched);
    eprintln!(
        "EVIDENCE({evidence}) profile={} survivors={} [{leaked:?}]",
        launched.profile.display(),
        leaked.len()
    );
    assert!(
        clean,
        "{evidence}: {} process(es) from the launch's own tree are still alive: {:?} \
         (profile {})",
        leaked.len(),
        leaked,
        launched.profile.display()
    );

    let after = unrelated_browsers(
        &read_table("post-shutdown"),
        &launched.binary,
        &launched.needle,
    );
    eprintln!(
        "EVIDENCE(outsiders) before={} [{:?}] after={} [{after:?}]",
        launched.outsiders.len(),
        launched.outsiders,
        after.len()
    );
    for pid in &launched.outsiders {
        assert!(
            after.contains(pid),
            "process {pid}, which ran {} outside this launch's job, disappeared",
            launched.binary
        );
    }
}

#[cfg(windows)]
#[tokio::test]
async fn windows_shutdown_reaps_the_whole_browser_tree() {
    let Some(binary) = win_guard() else {
        return;
    };
    let mut launched = launch_tree(&binary).await;

    // The kernel is the authority: `shutdown` returns `Ok` only once the job
    // object reports no live members, so a leak fails this call outright.
    launched
        .browser
        .take()
        .expect("browser handle")
        .shutdown()
        .await
        .expect("shutdown must verify the job object is empty");

    verify_reaped(&launched, "after-shutdown");
}

#[cfg(windows)]
#[tokio::test]
async fn windows_dropping_the_handle_also_reaps_the_tree() {
    let Some(binary) = win_guard() else {
        return;
    };
    let mut launched = launch_tree(&binary).await;

    // No explicit shutdown: the only thing that can reap this tree is dropping
    // the handle, which closes the last job handle and fires
    // `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
    drop(launched.browser.take());

    verify_reaped(&launched, "after-drop");
}
