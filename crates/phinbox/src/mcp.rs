//! MCP server module — wraps the library in a single `phinbox_mcp` tool.

pub mod router;
pub mod shutdown;

pub use router::PhinboxMcp;