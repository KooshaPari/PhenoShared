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

#![cfg(unix)]

use std::{
    path::{Path, PathBuf},
    time::Duration,
};

use substrate_browser_cdp::{
    chrome_binary, processes_using_user_data_dir, ChromeProcess, LaunchOptions,
};

/// A throwaway directory for one launch.
///
/// Work artifacts belong under `~/CodeProjects/temp`, so prefer that as the
/// temp root and fall back to the platform temp dir when it is absent.
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

#[test]
fn the_scanner_only_matches_its_own_profile() {
    // A path nothing can be using must yield no pids; this is the scoping
    // guarantee every kill decision in `process_tree` leans on.
    let phantom = Path::new("/nonexistent/phenotype-cdp-no-such-profile-xyzzy");
    assert!(processes_using_user_data_dir(phantom).is_empty());
}

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

    // And the user's browsers were not touched.
    let outsiders_after = unrelated_browser_pids(&binary, &profile);
    for pid in &outsiders_before {
        assert!(
            outsiders_after.contains(pid),
            "process {pid} outside the launch's own group disappeared during shutdown"
        );
    }
}

#[tokio::test]
async fn dropping_the_handle_also_reaps_the_tree() {
    let Ok(binary) = chrome_binary() else {
        eprintln!("skipping: no Chrome/Chromium binary found");
        return;
    };

    let temp = scratch();
    let profile = temp.path().join("profile");
    let outsiders_before = unrelated_browser_pids(&binary, &profile);

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

    let outsiders_after = unrelated_browser_pids(&binary, &profile);
    for pid in &outsiders_before {
        assert!(
            outsiders_after.contains(pid),
            "process {pid} outside the launch's own group disappeared"
        );
    }
}
