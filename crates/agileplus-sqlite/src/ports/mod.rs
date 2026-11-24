//! AgilePlus SQLite adapter ports module.
//!
//! This module organizes the SQLite adapter implementation into separate files.
//!
//! - `adapter.rs` - Core `SqliteStorageAdapter` struct definition
//! - `storage_port.rs` - `StoragePort` trait implementation
//! - `content_storage.rs` - `ContentStoragePort` trait implementation
//!
//! Traceability: WP06

pub mod adapter;
pub mod content_storage;
pub mod storage_port;

// Re-export the adapter type for convenience
pub use adapter::SqliteStorageAdapter;
