use crate::{AutomationEvent, Result, Viewport};

/// Desktop automation trait.
/// Implemented by: macOS (native), Windows (native), Linux (X11/Wayland).
#[async_trait::async_trait]
pub trait DesktopAutomator: Send + Sync {
    /// Get current viewport dimensions.
    async fn get_viewport(&self) -> Result<Viewport>;

    /// Take a screenshot.
    async fn screenshot(&self, path: &str) -> Result<()>;

    /// Execute pointer input.
    async fn pointer(&self, event: &crate::input::PointerInput) -> Result<()>;

    /// Execute text input.
    async fn text(&self, event: &crate::input::TextInput) -> Result<()>;

    /// Record automation event for audit log.
    async fn record_event(&self, event: AutomationEvent) -> Result<()>;
}

/// Mobile automation trait.
/// Implemented by: iOS (via XCTest), Android (via UiAutomator).
#[async_trait::async_trait]
pub trait MobileAutomator: Send + Sync {
    /// Get current viewport (screen dimensions).
    async fn get_viewport(&self) -> Result<Viewport>;

    /// Take a screenshot.
    async fn screenshot(&self, path: &str) -> Result<()>;

    /// Tap screen at coordinates.
    async fn tap(&self, x: i32, y: i32) -> Result<()>;

    /// Swipe from (x1, y1) to (x2, y2).
    async fn swipe(&self, x1: i32, y1: i32, x2: i32, y2: i32) -> Result<()>;

    /// Input text.
    async fn input_text(&self, text: &str) -> Result<()>;

    /// Record automation event for audit log.
    async fn record_event(&self, event: AutomationEvent) -> Result<()>;
}

/// Sandbox / container automation trait.
/// Implemented by: nanoVMs, Docker, Firecracker, KVM VMs.
#[async_trait::async_trait]
pub trait SandboxAutomator: Send + Sync {
    /// Get sandbox metadata (image, resource limits).
    async fn get_metadata(&self) -> Result<SandboxMetadata>;

    /// Start the sandbox.
    async fn start(&self) -> Result<()>;

    /// Stop the sandbox.
    async fn stop(&self) -> Result<()>;

    /// Execute command inside sandbox.
    async fn exec(&self, cmd: &str) -> Result<String>;

    /// Get current resource usage (CPU, memory, disk).
    async fn resource_usage(&self) -> Result<ResourceUsage>;

    /// Record automation event for audit log.
    async fn record_event(&self, event: AutomationEvent) -> Result<()>;
}

/// Sandbox metadata.
#[derive(Debug, Clone)]
pub struct SandboxMetadata {
    pub id: String,
    pub image: String,
    pub cpu_limit: u32,
    pub memory_limit_mb: u32,
    pub disk_limit_mb: Option<u32>,
}

/// Resource usage snapshot.
#[derive(Debug, Clone)]
pub struct ResourceUsage {
    pub cpu_percent: f64,
    pub memory_mb: u32,
    pub disk_mb: Option<u32>,
}
