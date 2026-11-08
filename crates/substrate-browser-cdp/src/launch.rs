//! Chrome launch: spawn a real Chrome against a caller-owned user data
//! directory and hand back its DevTools endpoint.
//!
//! The launcher deliberately owns nothing about profiles. The caller passes the
//! user data directory, which is how a profile *generation* from
//! `substrate-browser` becomes an actual isolated browser instance.

use std::{
    path::{Path, PathBuf},
    process::Stdio,
    time::Duration,
};

use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, BufReader},
    process::{Child, Command},
};

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
}

impl std::fmt::Debug for ChromeProcess {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ChromeProcess")
            .field("pid", &self.child.id())
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

        if options.headless {
            command.arg("--headless=new");
        }

        // Positional arguments last: Chrome treats a trailing token as a URL.
        command.arg("about:blank").args(&options.extra_args);

        let mut child = command.spawn().map_err(|err| CdpError::Launch {
            binary: binary.display().to_string(),
            source: err,
        })?;

        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| CdpError::Protocol("chrome stderr was not piped".into()))?;
        let stdout = child.stdout.take();

        let ws_url = match wait_for_endpoint(stderr, options.connect_timeout).await {
            Ok(url) => url,
            Err(err) => {
                let _ = child.kill().await;
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
        })
    }

    /// Terminate Chrome and wait for it to exit.
    pub async fn shutdown(mut self) -> Result<()> {
        let _ = self.child.kill().await;
        let _ = self.child.wait().await;
        Ok(())
    }
}

impl Drop for ChromeProcess {
    fn drop(&mut self) {
        // `kill_on_drop` already covers the common path; this makes the intent
        // explicit and also reaps the child when the runtime is still alive.
        let _ = self.child.start_kill();
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
