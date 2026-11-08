// SPDX-License-Identifier: MIT OR Apache-2.0

//! PhenoMCP binary entrypoint.
//!
//! `pheno-mcp` is the Model Context Protocol server binary. As of
//! 2026-06-19 the binary is a thin wrapper that boots a `ProviderRegistry`
//! populated with the canonical `OpenAICompatProvider` and prints the
//! registry contents. This scaffold will be expanded into the full MCP
//! request loop in a follow-up track.

mod provider;

fn main() {
    let registry = provider::build_default_registry().unwrap_or_else(|e| {
        eprintln!("pheno-mcp: failed to build provider registry: {e}");
        Default::default()
    });
    println!("pheno-mcp: providers = {:?}", registry.names());
}