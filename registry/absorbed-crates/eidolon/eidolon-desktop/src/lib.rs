//! Eidolon Desktop — macOS, Windows, Linux automation.

#[cfg(not(target_os = "macos"))]
use eidolon_core::traits::DesktopAutomator;
#[cfg(not(target_os = "macos"))]
use eidolon_core::{AutomationEvent, Result, Viewport};

#[cfg(target_os = "macos")]
mod macos;

#[cfg(target_os = "macos")]
pub use macos::MacOSClient as DesktopClient;

#[cfg(not(target_os = "macos"))]
use eidolon_core::traits::DesktopAutomator;
#[cfg(not(target_os = "macos"))]
use eidolon_core::{AutomationEvent, Result, Viewport};

#[cfg(not(target_os = "macos"))]
/// Desktop automation implementer (cross-platform stub).
pub struct DesktopClient {
    platform: String,
}

#[cfg(not(target_os = "macos"))]
impl DesktopClient {
    pub fn new(platform: &str) -> Self {
        Self {
            platform: platform.to_string(),
        }
    }
}

#[cfg(not(target_os = "macos"))]
#[async_trait::async_trait]
impl DesktopAutomator for DesktopClient {
    async fn get_viewport(&self) -> Result<Viewport> {
        Ok(Viewport::desktop_fhd())
    }

    async fn screenshot(&self, path: &str) -> Result<()> {
        log::info!("Taking screenshot to {} (stub)", path);
        Ok(())
    }

    async fn pointer(&self, event: &eidolon_core::input::PointerInput) -> Result<()> {
        log::info!(
            "Pointer event: ({}, {}) action={} (stub)",
            event.x,
            event.y,
            event.action
        );
        Ok(())
    }

    async fn text(&self, event: &eidolon_core::input::TextInput) -> Result<()> {
        log::info!(
            "Text event: type={} text={} (stub)",
            event.input_type,
            event.text
        );
        Ok(())
    }

    async fn record_event(&self, event: AutomationEvent) -> Result<()> {
        log::debug!("Recorded event: {:?}", event);
        Ok(())
    }
}
