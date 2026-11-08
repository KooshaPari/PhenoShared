//! Chrome launch: spawn a real Chrome against a caller-owned user data
//! directory and hand back its DevTools endpoint.
//!
//! The launcher deliberately owns nothing about profiles. The caller passes the
//! user data directory, which is how a profile *generation* from
//! `substrate-browser` becomes an actual isolated browser instance.
//!
//! Chrome is a process *tree*, not a process. On Unix the launcher therefore
//! spawns it in its own process group so shutdown can signal the renderer, GPU
//! and utility children along with the parent; see [`crate::process_tree`].

use std::{
    path::{Path, PathBuf},
    process::Stdio,
    time::Duration,
};

use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, BufReader},
    process::{Child, Command},
};

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

impl LaunchOptions {
    /// Options for a headless browser using `user_data_dir`.
    pub fn headless(user_data_dir: impl Into<PathBuf>) -> Self {
        Self {
            user_data_dir: user_data_dir.into(),
            headless: true,
            extra_args: Vec::new(),
            connect_timeout: Duration::from_secs(20),
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

/// A running Chrome, killed on drop.
pub struct ChromeProcess {
    child: Child,
    ws_url: String,
    user_data_dir: PathBuf,
    /// Process group created for this launch (`None` when it could not be
    /// established, in which case shutdown falls back to signalling the direct
    /// child only).
    process_group: Option<u32>,
}

impl std::fmt::Debug for ChromeProcess {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ChromeProcess")
            .field("pid", &self.child.id())
            .field("process_group", &self.process_group)
            .field("ws_url", &self.ws_url)
            .field("user_data_dir", &self.user_data_dir)
            .finish()
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
    /// signal the direct child (the historical, leaky behaviour).
    pub fn process_group(&self) -> Option<u32> {
        self.process_group
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
        let process_group = child.id().filter(|pid| {
            let Ok(pid) = libc::pid_t::try_from(*pid) else {
                return false;
            };
            // SAFETY: `getpgid` is a read-only syscall on a pid we just spawned.
            unsafe { libc::getpgid(pid) == pid }
        });
        #[cfg(not(unix))]
        let process_group: Option<u32> = None;

        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| CdpError::Protocol("chrome stderr was not piped".into()))?;
        let stdout = child.stdout.take();

        let ws_url = match wait_for_endpoint(stderr, options.connect_timeout).await {
            Ok(url) => url,
            Err(err) => {
                let _ = shutdown_tree(&mut child, process_group, &options.user_data_dir).await;
                return Err(err);
            },
        };
        if let Some(stdout) = stdout {
            spawn_drain(stdout);
        }

        Ok(Self {
            child,
            ws_url,
            user_data_dir: options.user_data_dir.clone(),
            process_group,
        })
    }

    /// Terminate Chrome *and its whole process tree*, then wait for it to be
    /// gone.
    ///
    /// The call does not return success until no live process references this
    /// launch's `--user-data-dir`, so a caller that reports "browser closed"
    /// is reporting a measurement rather than an intention.
    ///
    /// Windows: only the direct child is signalled (`Child::kill` + `wait`).
    /// Job-object based tree termination is not implemented here, so a Windows
    /// release can still leave renderers behind; the Unix defect this fixes was
    /// observed on macOS.
    pub async fn shutdown(mut self) -> Result<()> {
        let group = self.process_group.take();
        shutdown_tree(&mut self.child, group, &self.user_data_dir).await
    }
}

impl Drop for ChromeProcess {
    fn drop(&mut self) {
        // A dropped handle must not orphan a browser tree. Signal the group
        // first (sync syscall, safe from `Drop`), then let `kill_on_drop` reap
        // the direct child.
        #[cfg(unix)]
        if let Some(pgid) = self.process_group {
            if process_tree::group_exists(pgid) {
                let _ = process_tree::signal_group(pgid, libc::SIGKILL);
            }
        }
        let _ = self.child.start_kill();
    }
}

/// Terminate `child`, plus its process group when one was established.
async fn shutdown_tree(child: &mut Child, group: Option<u32>, user_data_dir: &Path) -> Result<()> {
    #[cfg(not(unix))]
    let _ = (group, user_data_dir);

    let mut outcome = Ok(());
    #[cfg(unix)]
    if let Some(pgid) = group {
        // Group termination already proves the tree is gone; the direct child
        // still has to be reaped below so no zombie is left behind.
        outcome = process_tree::terminate_group(pgid, user_data_dir).await;
    }

    let _ = child.kill().await;
    let _ = child.wait().await;
    outcome
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
