//! EwmhAdapter — Linux window enumeration via xcap (EWMH/x11rb-backed).
//! Implements WindowPort for Linux.
//!
//! Full x11rb EWMH implementation for window focus is a TODO;
//! enumeration is covered by xcap.

use crate::domain::window::{WindowError, WindowFilter, WindowInfo};
use crate::ports::WindowPort;
use async_trait::async_trait;
use tracing::{instrument, warn};

pub struct EwmhAdapter;

impl EwmhAdapter {
    pub fn new() -> Self {
        Self
    }
}

impl Default for EwmhAdapter {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl WindowPort for EwmhAdapter {
    #[instrument(name = "ewmh.list_windows", skip(self))]
    async fn list_windows(&self) -> Result<Vec<WindowInfo>, WindowError> {
        tokio::task::spawn_blocking(|| -> Result<Vec<WindowInfo>, WindowError> {
            let windows =
                xcap::Window::all().map_err(|e| WindowError::EnumerationFailed(e.to_string()))?;
            // xcap 0.9 returns every accessor as `XCapResult<_>`. A window can
            // disappear between `Window::all` and the per-window query, so a
            // single failure skips that window instead of failing the whole
            // enumeration.
            Ok(windows.into_iter().filter_map(describe_window).collect())
        })
        .await
        .map_err(|e| WindowError::Failed(format!("spawn_blocking panic: {e}")))?
    }

    #[instrument(name = "ewmh.find_window", skip(self))]
    async fn find_window(&self, filter: WindowFilter) -> Result<Option<WindowInfo>, WindowError> {
        let all = self.list_windows().await?;
        let found = all.into_iter().find(|w| {
            let title_match = filter
                .title
                .as_ref()
                .map_or(true, |t| w.title.to_lowercase().contains(&t.to_lowercase()));
            let pid_match = filter.pid.map_or(true, |p| w.pid == p);
            title_match && pid_match
        });
        Ok(found)
    }

    #[instrument(name = "ewmh.focus_window", skip(self))]
    async fn focus_window(&self, _hwnd: usize) -> Result<(), WindowError> {
        // TODO: implement using x11rb _NET_ACTIVE_WINDOW ClientMessage.
        warn!("windows.focus: not yet implemented on Linux (stub)");
        Ok(())
    }
}

/// Query one xcap window, returning `None` (and logging) if it went away.
#[instrument(name = "ewmh.describe_window", skip_all)]
fn describe_window(window: xcap::Window) -> Option<WindowInfo> {
    match window_info(&window) {
        Ok(info) => Some(info),
        Err(err) => {
            warn!(%err, "windows.list: skipping window that could not be read");
            None
        },
    }
}

/// Read the real geometry / identity of a window from xcap.
///
/// Values come from the compositor, not from defaults: the caller decides
/// whether a failure is fatal.
fn window_info(window: &xcap::Window) -> Result<WindowInfo, xcap::XCapError> {
    Ok(WindowInfo {
        hwnd: window.id()? as usize,
        title: window.title()?,
        pid: window.pid()?,
        x: window.x()?,
        y: window.y()?,
        width: window.width()? as i32,
        height: window.height()? as i32,
        // xcap only returns visible windows
        visible: true,
    })
}
