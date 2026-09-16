//! Eidolon Mobile — iOS and Android automation.
//!
//! Phase-3 Migration (per findings/2026-06-17-eidolon-absorption.md):
//! - kmobile-core's `DevicePort` is superseded by Eidolon's native
//!   `DeviceManager` (see `kmobile_bridge` module). kmobile-core ports
//!   are forwarded via the same async fn signatures.
//! - iOS XCTest and Android UiAutomator integration continues from
//!   `crates/kmobile/ios/test_support/` and `crates/kmobile/android/uiautomator/`.
//! - Native bridge: Rust FFI stubs prepared in `eidolon-mobile/src/native/`.

use eidolon_core::traits::MobileAutomator;
use eidolon_core::{AutomationEvent, Result, Viewport};

pub mod kmobile_bridge;
pub mod native;

pub use kmobile_bridge::{
    DeviceInfo, DeviceManager, InMemoryDeviceManager, Modality, TestRunReport,
};

/// Mobile automation implementer.
pub struct MobileClient {
    #[allow(dead_code)]
    platform: String,
}

impl MobileClient {
    pub fn new(platform: &str) -> Self {
        Self {
            platform: platform.to_string(),
        }
    }
}

#[async_trait::async_trait]
impl MobileAutomator for MobileClient {
    async fn get_viewport(&self) -> Result<Viewport> {
        // TODO: Integrate iOS XCTest / Android UiAutomator
        Ok(Viewport::mobile_fhd())
    }

    async fn screenshot(&self, path: &str) -> Result<()> {
        log::info!("Taking mobile screenshot to {}", path);
        Ok(())
    }

    async fn tap(&self, x: i32, y: i32) -> Result<()> {
        log::info!("Tapping ({}, {})", x, y);
        Ok(())
    }

    async fn swipe(&self, x1: i32, y1: i32, x2: i32, y2: i32) -> Result<()> {
        log::info!("Swiping from ({}, {}) to ({}, {})", x1, y1, x2, y2);
        Ok(())
    }

    async fn input_text(&self, text: &str) -> Result<()> {
        log::info!("Inputting text: {}", text);
        Ok(())
    }

    async fn record_event(&self, event: AutomationEvent) -> Result<()> {
        log::debug!("Recorded mobile event: {:?}", event);
        Ok(())
    }
}
