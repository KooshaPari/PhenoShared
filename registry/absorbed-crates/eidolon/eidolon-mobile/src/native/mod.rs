//! Native platform adapters for iOS and Android.
//!
//! Placeholder module for Phase-2 extraction from kmobile:
//! - ios.rs: XCTest framework bridge (kmobile/ios/test_support/)
//! - android.rs: UiAutomator framework bridge (kmobile/android/uiautomator/)

/// iOS XCTest framework adapter trait.
pub trait IosTestAdapter {
    /// Execute XCTest and capture results.
    fn run_test(&self, suite: &str) -> Result<String, String>;

    /// Get current viewport from XCTest introspection.
    fn get_viewport(&self) -> Result<(u32, u32), String>;
}

/// Android UiAutomator framework adapter trait.
pub trait AndroidTestAdapter {
    /// Execute UiAutomator command.
    fn execute(&self, cmd: &str) -> Result<String, String>;

    /// Get device viewport via dumpsys.
    fn get_viewport(&self) -> Result<(u32, u32), String>;
}

// TODO: impl IosTestAdapter { ... } — integrate kmobile XCTest wrappers
// TODO: impl AndroidTestAdapter { ... } — integrate kmobile UiAutomator wrappers
