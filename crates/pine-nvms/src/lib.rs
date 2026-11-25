//! pine-nvms — nvms microVM integration adapter.
//!
//! Provides a runtime adapter for integrating with nvms microVMs.
//!
//! # Example
//!
//! ```
//! use pine_nvms::NvmsRuntime;
//!
//! let runtime = NvmsRuntime::new();
//! ```

#![warn(missing_docs)]

/// A runtime adapter for nvms microVM integration.
///
/// This type provides the entry point for connecting Pine to the
/// nvms microVM backend.
///
/// # Example
///
/// ```
/// use pine_nvms::NvmsRuntime;
///
/// let runtime = NvmsRuntime::new();
/// ```
pub struct NvmsRuntime;

impl NvmsRuntime {
    /// Create a new nvms runtime adapter.
    ///
    /// # Example
    ///
    /// ```
    /// use pine_nvms::NvmsRuntime;
    ///
    /// let runtime = NvmsRuntime::new();
    /// ```
    pub fn new() -> Self {
        Self
    }
}

impl Default for NvmsRuntime {
    fn default() -> Self {
        Self::new()
    }
}
