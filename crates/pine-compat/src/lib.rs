//! pine-compat — Compatibility shim (Wine-like translation).
//!
//! Provides a [`CompatibilityLayer`] that can be used to bridge
//! differences between host and guest environments.
//!
//! # Example
//!
//! ```
//! use pine_compat::CompatibilityLayer;
//!
//! let layer = CompatibilityLayer::new();
//! ```

#![warn(missing_docs)]

/// A compatibility layer for bridging host and guest environments.
///
/// This layer is responsible for translating or emulating behaviour
/// that differs between the native host and the guest environment.
///
/// # Example
///
/// ```
/// use pine_compat::CompatibilityLayer;
///
/// let layer = CompatibilityLayer::new();
/// ```
pub struct CompatibilityLayer;

impl CompatibilityLayer {
    /// Create a new compatibility layer.
    ///
    /// # Example
    ///
    /// ```
    /// use pine_compat::CompatibilityLayer;
    ///
    /// let layer = CompatibilityLayer::new();
    /// ```
    pub fn new() -> Self {
        Self
    }
}

impl Default for CompatibilityLayer {
    fn default() -> Self {
        Self::new()
    }
}
