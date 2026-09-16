//! Core domain types.
//!
//! These types are used across the Pine ecosystem to identify processes
//! and system calls.
//!
//! # Example
//!
//! ```
//! use pine_core::types::{ProcessId, SyscallNumber};
//!
//! let pid = ProcessId(42);
//! let num = SyscallNumber(0x80);
//! ```

/// A unique identifier for a process.
///
/// This is a thin wrapper around a `u32` value.
///
/// # Example
///
/// ```
/// use pine_core::types::ProcessId;
///
/// let pid = ProcessId(1234);
/// assert_eq!(pid.0, 1234);
/// ```
pub struct ProcessId(pub u32);

/// A system call number.
///
/// This is a thin wrapper around a `u32` value representing a raw
/// syscall number.
///
/// # Example
///
/// ```
/// use pine_core::types::SyscallNumber;
///
/// let num = SyscallNumber(0);
/// assert_eq!(num.0, 0);
/// ```
pub struct SyscallNumber(pub u32);
