//! Stub for the `agileplus-mcp` crate.
//!
//! The actual MCP server is implemented inside `agileplus-cli` (under
//! `crates/agileplus-cli/src/mcp/`). This stub exists so the workspace
//! member entry in the root `Cargo.toml` resolves, and so other crates
//! that depend on `agileplus-mcp` as a path dep can still be built.

pub fn stub() -> &'static str {
    "agileplus-mcp stub — see crates/agileplus-cli/src/mcp for the real implementation"
}
