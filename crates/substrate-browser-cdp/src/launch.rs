//! Chrome launch: spawn a real Chrome against a caller-owned user data
//! directory and hand back its DevTools endpoint.
//!
//! The launcher deliberately owns nothing about profiles. The caller passes the
//! user data directory, which is how a profile *generation* from
//! `substrate-browser` becomes an actual isolated browser instance.
//!
//! Chrome is a process *tree*, not a process. Whole-tree shutdown is therefore
//! platform-specific: on Unix the launcher spawns Chrome in its own process
//! group so shutdown can signal the renderer, GPU and utility children along
//! with the parent (`crate::process_tree`); on Windows the launcher assigns
//! Chrome to a job object and terminates the job (`crate::job_object`).

use std::{
    path::{Path, PathBuf},
    process::Stdio,
    time::Duration,
};

use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, BufReader},
    process::{Child, Command},
};

#[cfg(windows)]
use crate::job_object::{self, JobHandle};
#[cfg(unix)]
use crate::process_tree;
use crate::{CdpError, Result};

/// How to start Chrome.
#[derive(Debug, Clone)]
pub struct LaunchOptions {
    /// Browser data directory. Every generation must get its own.
    pub user_data_dir: PathBuf,
    /// Run without a window. Defaults to `true`.
    pub headless: bool,
    /// Extra command line arguments appended last.
    pub extra_args: Vec<String>,
    /// How long to wait for Chrome to print its DevTools endpoint.
    pub connect_timeout: Duration,
}

/// Environment variable that overrides the launch connect budget, in seconds.
///
/// A busy host can take far longer than the default to publish a DevTools
/// endpoint (macOS Spotlight and WindowServer contention are the classic
/// cause), which fails an entire test binary for reasons unrelated to the
/// code under test. CI therefore raises the budget for its test step without
/// changing production behaviour, which keeps the 20s default.
pub const LAUNCH_TIMEOUT_ENV: &str = "SUBSTRATE_BROWSER_LAUNCH_TIMEOUT_SECS";

/// The default launch connect budget.
pub const DEFAULT_CONNECT_TIMEOUT: Duration = Duration::from_secs(20);

/// Resolve the launch connect budget from the environment.
///
/// Falls back to [`DEFAULT_CONNECT_TIMEOUT`] when the variable is unset,
/// empty, unparseable, or zero: a malformed override must never panic and
/// must never disable the wait entirely.
fn connect_timeout_from_env() -> Duration {
    parse_connect_timeout(std::env::var(LAUNCH_TIMEOUT_ENV).ok().as_deref())
}

/// Interpret a raw override value, falling back to the default.
///
/// Split out from [`connect_timeout_from_env`] so the fallback rules are
/// testable without mutating the process environment.
fn parse_connect_timeout(raw: Option<&str>) -> Duration {
    raw.and_then(|raw| raw.trim().parse::<u64>().ok())
        .filter(|secs| *secs > 0)
        .map(Duration::from_secs)
        .unwrap_or(DEFAULT_CONNECT_TIMEOUT)
}

impl LaunchOptions {
    /// Options for a headless browser using `user_data_dir`.
    pub fn headless(user_data_dir: impl Into<PathBuf>) -> Self {
        Self {
            user_data_dir: user_data_dir.into(),
            headless: true,
            extra_args: Vec::new(),
            connect_timeout: connect_timeout_from_env(),
        }
    }

    /// Options for a visible browser using `user_data_dir`.
    pub fn headed(user_data_dir: impl Into<PathBuf>) -> Self {
        Self {
            headless: false,
            ..Self::headless(user_data_dir)
        }
    }
}

/// The platform mechanism that owns this launch's whole process tree.
///
/// Unix: the process group created by `Command::process_group`, verified to be
/// led by the spawned child. Windows: the job object the child was assigned to,
/// which every descendant inherits. An empty scope means none could be
/// established, in which case shutdown degrades to killing the direct child -
/// the historical, leaky path.
struct TreeScope {
    #[cfg(unix)]
    process_group: Option<u32>,
    #[cfg(windows)]
    job: Option<JobHandle>,
}

impl TreeScope {
    /// Terminate everything in scope, then reap the direct child.
    ///
    /// Whole-tree termination already proves the tree is gone; the direct child
    /// is still reaped below so no zombie is left behind.
    async fn terminate(&self, child: &mut Child, user_data_dir: &Path) -> Result<()> {
        #[cfg(unix)]
        let outcome = match self.process_group {
            Some(pgid) => process_tree::terminate_group(pgid, user_data_dir).await,
            None => Ok(()),
        };
        #[cfg(windows)]
        let outcome = match self.job.as_ref() {
            Some(job) => job_object::terminate_tree(job, user_data_dir).await,
            None => Ok(()),
        };

        let _ = child.kill().await;
        let _ = child.wait().await;
        outcome
    }
}

/// A running Chrome, killed on drop.
pub struct ChromeProcess {
    /// Dropped before `child` so that on Windows the job's `KILL_ON_JOB_CLOSE`
    /// fires while the direct-child handle is still open.
    scope: TreeScope,
    child: Child,
    ws_url: String,
    user_data_dir: PathBuf,
}

impl std::fmt::Debug for ChromeProcess {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let mut debug = f.debug_struct("ChromeProcess");
        debug
            .field("pid", &self.child.id())
            .field("process_group", &self.process_group())
            .field("ws_url", &self.ws_url)
            .field("user_data_dir", &self.user_data_dir);
        #[cfg(windows)]
        debug.field("job_object", &self.scope.job.is_some());
        debug.finish()
    }
}

impl ChromeProcess {
    /// The browser-level DevTools WebSocket URL.
    pub fn ws_url(&self) -> &str {
        &self.ws_url
    }

    /// The data directory this process was started with.
    pub fn user_data_dir(&self) -> &Path {
        &self.user_data_dir
    }

    /// Operating system process id.
    pub fn pid(&self) -> Option<u32> {
        self.child.id()
    }

    /// The process group this launch created, if any.
    ///
    /// `None` means the group could not be established and shutdown can only
    /// signal the direct child (the historical, leaky behaviour). Always `None`
    /// on Windows, where a job object is the equivalent authority and there is
    /// no group id to report.
    pub fn process_group(&self) -> Option<u32> {
        #[cfg(unix)]
        {
            self.scope.process_group
        }
        #[cfg(not(unix))]
        {
            None
        }
    }

    /// Launch Chrome and wait until it reports a DevTools endpoint.
    pub async fn launch(options: &LaunchOptions) -> Result<Self> {
        let binary = chrome_binary()?;
        std::fs::create_dir_all(&options.user_data_dir)?;

        let mut command = Command::new(&binary);
        command
            .arg("--remote-debugging-port=0")
            .arg(format!(
                "--user-data-dir={}",
                options.user_data_dir.display()
            ))
            .args([
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-sync",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--metrics-recording-only",
                "--password-store=basic",
                "--use-mock-keychain",
            ])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true);

        // Give Chrome its own process group so the entire tree can be
        // signalled at once. Children inherit the group, so a single
        // `kill(-pgid, …)` reaches renderers and utilities too.
        #[cfg(unix)]
        command.process_group(0);

        if options.headless {
            command.arg("--headless=new");
        }

        // Positional arguments last: Chrome treats a trailing token as a URL.
        command.arg("about:blank").args(&options.extra_args);

        let mut child = command.spawn().map_err(|err| CdpError::Launch {
            binary: binary.display().to_string(),
            source: err,
        })?;

        // `process_group(0)` makes the child the leader of a new group whose id
        // equals its pid. Verify that rather than assume it: if the group was
        // not established, shutdown must not signal an unrelated group id.
        #[cfg(unix)]
        let scope = TreeScope {
            process_group: child.id().filter(|pid| {
                let Ok(pid) = libc::pid_t::try_from(*pid) else {
                    return false;
                };
                // SAFETY: `getpgid` is a read-only syscall on a pid we just spawned.
                unsafe { libc::getpgid(pid) == pid }
            }),
        };

        // Windows has no `process_group`. A job object is the equivalent
        // authority: descendants inherit membership at creation, so
        // `TerminateJobObject` reaches renderers and utilities too. Assign it
        // immediately after spawn, while Chrome has not yet started children.
        #[cfg(windows)]
        let scope = TreeScope {
            job: child.raw_handle().and_then(|process| {
                JobHandle::create()
                    .and_then(|job| job.assign(process).map(|()| job))
                    .ok()
            }),
        };

        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| CdpError::Protocol("chrome stderr was not piped".into()))?;
        let stdout = child.stdout.take();

        let ws_url = match wait_for_endpoint(stderr, options.connect_timeout).await {
            Ok(url) => url,
            Err(err) => {
                let _ = scope.terminate(&mut child, &options.user_data_dir).await;
                return Err(err);
            },
        };
        if let Some(stdout) = stdout {
            spawn_drain(stdout);
        }

        Ok(Self {
            scope,
            child,
            ws_url,
            user_data_dir: options.user_data_dir.clone(),
        })
    }

    /// Terminate Chrome *and its whole process tree*, then wait for it to be
    /// gone.
    ///
    /// The call does not return success until no live process references this
    /// launch's `--user-data-dir`, so a caller that reports "browser closed"
    /// is reporting a measurement rather than an intention.
    ///
    /// Mechanism per platform:
    /// - Unix: `SIGTERM` the launch's process group, bounded wait, `SIGKILL` the
    ///   group, bounded wait, then `SIGKILL` stragglers matched by the launch's
    ///   unique profile path. Exercised by the `process_tree` tests.
    /// - Windows: `TerminateJobObject` on the launch's job object, bounded wait,
    ///   repeat, then terminate any remaining job member. A `#[cfg(windows)]`
    ///   test in `tests/process_tree.rs` covers this, and
    ///   `.github/workflows/windows-browser-tree.yml` runs it on
    ///   `windows-latest`; no macOS or Linux host can.
    ///
    /// If no scope could be established the direct child is killed and waited
    /// for as before, which can still leave renderers behind.
    pub async fn shutdown(mut self) -> Result<()> {
        // `self` owns a `Drop` impl, so the child is borrowed rather than moved;
        // `Drop` then re-runs harmlessly on an already-reaped process.
        self.scope
            .terminate(&mut self.child, &self.user_data_dir)
            .await
    }
}

impl Drop for ChromeProcess {
    fn drop(&mut self) {
        // A dropped handle must not orphan a browser tree.
        //
        // Unix: signal the group first (sync syscall, safe from `Drop`), then
        // let `kill_on_drop` reap the direct child.
        #[cfg(unix)]
        if let Some(pgid) = self.scope.process_group {
            if process_tree::group_exists(pgid) {
                let _ = process_tree::signal_group(pgid, libc::SIGKILL);
            }
        }
        let _ = self.child.start_kill();
        // Windows needs no explicit call here: dropping `scope` closes the last
        // job handle and `KILL_ON_JOB_CLOSE` terminates every remaining member.
        // Fields drop in declaration order, so the job closes before `child`.
    }
}

async fn wait_for_endpoint(
    stderr: tokio::process::ChildStderr,
    timeout: Duration,
) -> Result<String> {
    const MARKER: &str = "DevTools listening on ";
    let mut lines = BufReader::new(stderr).lines();

    let read = async {
        while let Ok(Some(line)) = lines.next_line().await {
            if let Some(rest) = line.find(MARKER).map(|idx| &line[idx + MARKER.len()..]) {
                return Ok(rest.trim().to_string());
            }
        }
        Err(CdpError::Protocol(
            "chrome exited before reporting a DevTools endpoint".into(),
        ))
    };

    match tokio::time::timeout(timeout, read).await {
        Ok(outcome) => outcome,
        Err(_) => Err(CdpError::Timeout(format!(
            "chrome did not report a DevTools endpoint within {}s",
            timeout.as_secs()
        ))),
    }
}

fn spawn_drain<R>(mut reader: R)
where
    R: tokio::io::AsyncRead + Unpin + Send + 'static,
{
    tokio::spawn(async move {
        let mut buffer = [0u8; 8192];
        // Chrome is chatty on stdout/stderr. A full pipe would stall it, so keep
        // reading until the process closes the descriptor.
        while matches!(reader.read(&mut buffer).await, Ok(n) if n > 0) {}
    });
}

/// Locate a Chrome/Chromium binary.
///
/// `CHROME_BIN` wins, then the platform default locations.
pub fn chrome_binary() -> Result<PathBuf> {
    if let Ok(explicit) = std::env::var("CHROME_BIN") {
        if !explicit.trim().is_empty() {
            return Ok(PathBuf::from(explicit));
        }
    }

    let mut candidates: Vec<PathBuf> = Vec::new();
    #[cfg(target_os = "macos")]
    {
        for name in [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ] {
            candidates.push(PathBuf::from(name));
        }
    }
    #[cfg(target_os = "linux")]
    {
        for name in [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
        ] {
            candidates.push(PathBuf::from(name));
        }
    }
    #[cfg(target_os = "windows")]
    {
        for name in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ] {
            candidates.push(PathBuf::from(name));
        }
    }

    for candidate in candidates {
        if candidate.is_absolute() {
            if candidate.is_file() {
                return Ok(candidate);
            }
        } else if which(&candidate) {
            return Ok(candidate);
        }
    }

    Err(CdpError::NoBrowser)
}

fn which(name: &Path) -> bool {
    let Some(paths) = std::env::var_os("PATH") else {
        return false;
    };
    std::env::split_paths(&paths).any(|dir| {
        let candidate = dir.join(name);
        candidate.is_file()
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn launch_timeout_defaults_when_unset() {
        assert_eq!(parse_connect_timeout(None), DEFAULT_CONNECT_TIMEOUT);
        assert_eq!(DEFAULT_CONNECT_TIMEOUT, Duration::from_secs(20));
    }

    #[test]
    fn launch_timeout_accepts_a_positive_override() {
        assert_eq!(parse_connect_timeout(Some("90")), Duration::from_secs(90));
        assert_eq!(
            parse_connect_timeout(Some("  120  ")),
            Duration::from_secs(120)
        );
    }

    #[test]
    fn launch_timeout_falls_back_on_malformed_values() {
        for raw in [
            "",
            "   ",
            "abc",
            "-5",
            "1.5",
            "0",
            "999999999999999999999999",
        ] {
            assert_eq!(
                parse_connect_timeout(Some(raw)),
                DEFAULT_CONNECT_TIMEOUT,
                "malformed override {raw:?} must fall back to the default, not panic"
            );
        }
    }
}
