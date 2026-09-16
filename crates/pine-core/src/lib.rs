//! pine-core — Domain types and shared interfaces for Pine.
//!
//! This crate provides the foundational types and traits used across
//! the Pine ecosystem.
//!
//! # Example
//!
//! ```
//! use pine_core::types::{ProcessId, SyscallNumber};
//!
//! let pid = ProcessId(42);
//! let num = SyscallNumber(0x80);
//! ```

#![warn(missing_docs)]

pub mod observability;
pub mod ports;
pub mod traits;
pub mod types;

#[cfg(test)]
mod tests {
    use super::types::*;

    #[test]
    fn process_id_newtype() {
        let pid = ProcessId(42);
        assert_eq!(pid.0, 42);
    }

    #[test]
    fn syscall_number_newtype() {
        let num = SyscallNumber(0x80);
        assert_eq!(num.0, 0x80);
    }
}

#[cfg(test)]
mod proptests {
    use super::types::*;
    use proptest::prelude::*;

    proptest! {
        /// ProcessId wraps any u32 without transformation.
        #[test]
        fn process_id_roundtrip(value: u32) {
            let pid = ProcessId(value);
            assert_eq!(pid.0, value);
        }

        /// SyscallNumber wraps any u32 without transformation.
        #[test]
        fn syscall_number_roundtrip(value: u32) {
            let num = SyscallNumber(value);
            assert_eq!(num.0, value);
        }
    }
}
