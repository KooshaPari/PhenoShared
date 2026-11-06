//! # Driving Ports (Primary Ports)
//!
//! Interfaces that the application uses to interact with external actors.

/// CLI interface for the cache system
pub trait CliPort {
    /// Display cache entry
    fn display_entry(&self, key: &str, value: &str);

    /// Display statistics
    fn display_stats(&self, hits: u64, misses: u64, size: usize);

    /// Display error
    fn display_error(&self, error: &str);
}

/// HTTP/REST interface
pub trait HttpPort {
    /// Handle get request
    fn handle_get(&self, key: &str) -> Option<String>;

    /// Handle set request
    fn handle_set(&self, key: &str, value: &str) -> Result<(), String>;

    /// Handle delete request
    fn handle_delete(&self, key: &str) -> Result<(), String>;
}
