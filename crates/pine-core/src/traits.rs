//! Core domain traits (ports).
//!
//! These traits define the boundaries between Pine's subsystems.
//!
//! # Example
//!
//! ```
//! use pine_core::traits::{Loader, SyscallHandler};
//!
//! struct MyLoader;
//! impl Loader for MyLoader {
//!     fn load(&self, path: &str) -> Result<Vec<u8>, String> {
//!         Ok(vec![])
//!     }
//! }
//!
//! struct MyHandler;
//! impl SyscallHandler for MyHandler {
//!     fn handle(&self, _number: u32, _args: &[u64]) -> Result<u64, String> {
//!         Ok(0)
//!     }
//! }
//! ```

/// Loads binary data from a path.
///
/// Implementations may read from disk, memory, or a network source.
///
/// # Example
///
/// ```
/// use pine_core::traits::Loader;
///
/// struct MyLoader;
/// impl Loader for MyLoader {
///     fn load(&self, path: &str) -> Result<Vec<u8>, String> {
///         Ok(vec![1, 2, 3])
///     }
/// }
///
/// let loader = MyLoader;
/// let data = loader.load("/tmp/test.bin").unwrap();
/// assert_eq!(data, vec![1, 2, 3]);
/// ```
pub trait Loader {
    /// Load binary data from the given path.
    fn load(&self, path: &str) -> Result<Vec<u8>, String>;
}

/// Handles system calls.
///
/// Implementations translate raw syscall numbers into platform-specific
/// behaviour and return the result.
///
/// # Example
///
/// ```
/// use pine_core::traits::SyscallHandler;
///
/// struct MyHandler;
/// impl SyscallHandler for MyHandler {
///     fn handle(&self, number: u32, _args: &[u64]) -> Result<u64, String> {
///         Ok(number as u64)
///     }
/// }
///
/// let handler = MyHandler;
/// let result = handler.handle(42, &[]).unwrap();
/// assert_eq!(result, 42);
/// ```
pub trait SyscallHandler {
    /// Handle a syscall with the given number and arguments.
    fn handle(&self, number: u32, args: &[u64]) -> Result<u64, String>;
}
