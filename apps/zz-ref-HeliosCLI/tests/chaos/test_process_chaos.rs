//! Chaos test: Process failure simulation.
//!
//! Simulates process crashes, unexpected exits, signal handling, and
//! cascading process failures to verify system resilience.

use std::io;
use std::process::{Command, ExitStatus};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Barrier, Mutex};
use std::time::{Duration, Instant};

// ── Helpers ──────────────────────────────────────

/// Simulates a process crash by spawning a subprocess that panics.
fn spawn_crashing_process() -> io::Result<ExitStatus> {
    let output = Command::new("sh")
        .args(["-c", "panic 'simulated crash'"])
        .output()?;

    Ok(output.status)
}

/// Simulates a process that exits with an error code.
fn spawn_failing_process(exit_code: i32) -> io::Result<ExitStatus> {
    let output = Command::new("sh")
        .args(["-c", &format!("exit {}", exit_code)])
        .output()?;

    Ok(output.status)
}

/// Simulates a process that hangs (uses sleep as a proxy for infinite loop).
fn spawn_hanging_process(timeout_ms: u64) -> io::Result<ExitStatus> {
    let output = Command::new("sh")
        .args(["-c", &format!("sleep {}", timeout_ms / 1000 + 10)])
        .timeout(Duration::from_millis(timeout_ms))
        .output()?;

    Ok(output.status)
}

/// Simulates a process watchdog that monitors a flag and "kills" when triggered.
struct ProcessWatchdog {
    kill_flag: Arc<AtomicBool>,
    kill_count: Arc<AtomicUsize>,
    stop_flag: Arc<AtomicBool>,
}

impl ProcessWatchdog {
    fn new() -> Self {
        Self {
            kill_flag: Arc::new(AtomicBool::new(false)),
            kill_count: Arc::new(AtomicUsize::new(0)),
            stop_flag: Arc::new(AtomicBool::new(false)),
        }
    }

    fn trigger_kill(&self) {
        self.kill_flag.store(true, Ordering::Relaxed);
    }

    fn should_kill(&self) -> bool {
        self.kill_flag.load(Ordering::Relaxed)
    }

    fn stop(&self) {
        self.stop_flag.store(true, Ordering::Relaxed);
    }

    fn was_stopped(&self) -> bool {
        self.stop_flag.load(Ordering::Relaxed)
    }

    fn record_kill(&self) {
        self.kill_count.fetch_add(1, Ordering::Relaxed);
    }

    fn kill_count(&self) -> usize {
        self.kill_count.load(Ordering::Relaxed)
    }

    /// Run the watchdog loop (blocking). Call from a separate thread.
    fn run(&self) {
        loop {
            if self.was_stopped() {
                break;
            }
            if self.should_kill() {
                self.record_kill();
                break;
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }
}

// ── Tests ────────────────────────────────────────

#[test]
fn test_process_crash_detection() {
    let status = spawn_crashing_process().unwrap();
    assert!(
        !status.success(),
        "crashing process should return non-zero exit code"
    );
}

#[test]
fn test_process_error_exit_codes() {
    let codes = vec![1, 2, 127, 137, 255];
    for code in &codes {
        let status = spawn_failing_process(*code).unwrap();
        assert!(!status.success());
        assert_eq!(
            status.code(),
            Some(*code),
            "exit code should match for code {}",
            code
        );
    }
}

#[test]
fn test_process_timeout() {
    let start = Instant::now();
    let status = spawn_hanging_process(100).unwrap();
    let elapsed = start.elapsed();

    assert!(
        elapsed < Duration::from_secs(5),
        "process should have been killed quickly"
    );
}

#[test]
fn test_watchdog_kills_process() {
    let watchdog = ProcessWatchdog::new();
    let w = watchdog.clone_refs();

    let handle = std::thread::spawn(move || w.run());

    // Trigger kill
    watchdog.trigger_kill();
    handle.join().unwrap();

    assert!(
        watchdog.kill_count() > 0,
        "watchdog should have recorded at least one kill"
    );
}

#[test]
fn test_watchdog_no_kill_without_trigger() {
    let watchdog = ProcessWatchdog::new();
    let w = watchdog.clone_refs();

    let handle = std::thread::spawn(move || {
        let mut iterations = 0;
        loop {
            if watchdog.was_stopped() || iterations > 100 {
                break;
            }
            if watchdog.should_kill() {
                break;
            }
            std::thread::sleep(Duration::from_millis(5));
            iterations += 1;
        }
    });

    // Stop without triggering kill
    std::thread::sleep(Duration::from_millis(50));
    watchdog.stop();
    handle.join().unwrap();

    assert_eq!(watchdog.kill_count(), 0);
}

#[test]
fn test_cascading_process_failures() {
    let num_children = 5;
    let shared_failure = Arc::new(AtomicBool::new(false));
    let failed_count = Arc::new(AtomicUsize::new(0));
    let barrier = Arc::new(Barrier::new(num_children + 1));

    let mut handles = Vec::new();

    for i in 0..num_children {
        let sf = shared_failure.clone();
        let fc = failed_count.clone();
        let bar = barrier.clone();

        handles.push(std::thread::spawn(move || {
            bar.wait();

            // Wait a bit, then check for cascade
            for _ in 0..50 {
                if sf.load(Ordering::Relaxed) {
                    fc.fetch_add(1, Ordering::Relaxed);
                    return;
                }
                std::thread::sleep(Duration::from_millis(10));
            }
        }));
    }

    barrier.wait(); // Start all children

    // Simulate cascade trigger
    std::thread::sleep(Duration::from_millis(20));
    shared_failure.store(true, Ordering::Relaxed);

    for h in handles {
        h.join().unwrap();
    }

    let failed = failed_count.load(Ordering::Relaxed);
    assert_eq!(
        failed, num_children,
        "all {} children should have detected the cascade",
        num_children
    );
}

#[test]
fn test_rapid_process_spawn_and_kill() {
    let kill_flag = Arc::new(AtomicBool::new(false));
    let mut handles = Vec::new();

    for _ in 0..20 {
        let kf = kill_flag.clone();
        handles.push(std::thread::spawn(move || {
            loop {
                if kf.load(Ordering::Relaxed) {
                    return;
                }
                std::thread::yield_now();
            }
        }));
    }

    // Let them run briefly
    std::thread::sleep(Duration::from_millis(50));

    // Kill all
    kill_flag.store(true, Ordering::Relaxed);

    for h in handles {
        h.join().unwrap();
    }
}

#[test]
fn test_process_recovery_after_failure() {
    let mut recovery_attempts = 0;
    let max_retries = 5;
    let mut success = false;

    for attempt in 0..max_retries {
        recovery_attempts += 1;

        // Simulate: first N attempts fail, then succeed
        if attempt >= 3 {
            success = true;
            break;
        }
    }

    assert!(success, "should have recovered after retries");
    assert_eq!(recovery_attempts, 4);
}

#[test]
fn test_concurrent_watchdog_management() {
    let watchdogs: Vec<ProcessWatchdog> = (0..10).map(|_| ProcessWatchdog::new()).collect();

    let mut handles = Vec::new();

    for (i, wd) in watchdogs.iter().enumerate() {
        let w = wd.clone_refs();
        handles.push(std::thread::spawn(move || {
            // Each watchdog runs independently
            loop {
                if w.was_stopped() || w.should_kill() {
                    break;
                }
                std::thread::sleep(Duration::from_millis(2));
            }
        }));

        // Randomly trigger some watchdogs
        if i % 2 == 0 {
            wd.trigger_kill();
        } else {
            wd.stop();
        }
    }

    for h in handles {
        h.join().unwrap();
    }

    // Half should have been killed, half stopped
    let total_kills: usize = watchdogs.iter().map(|w| w.kill_count()).sum();
    assert!(total_kills >= 5, "expected at least 5 kills, got {}", total_kills);
}

// ── Helper trait for ProcessWatchdog ──────────────

impl ProcessWatchdog {
    fn clone_refs(&self) -> Self {
        Self {
            kill_flag: self.kill_flag.clone(),
            kill_count: self.kill_count.clone(),
            stop_flag: self.stop_flag.clone(),
        }
    }
}
