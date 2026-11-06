# MCP IDL — Polyglot Interface Definition

This directory is the canonical home for the Model Context Protocol IDL
**across all language runtimes** supported by PhenoFastMCP.

## Layout

```
core/mcp-idl/
├── proto/      # Source-of-truth Protocol Buffers / JSON Schemas
├── rust/       # Rust crate root for mcp-idl (generated from proto/)
├── go/         # Go module root for mcp-idl (generated from proto/)
└── more/       # Additional runtimes as added (swift, kotlin, …)
```

## Source-of-truth

`proto/` contains the upstream MCP spec as `.proto` files + a `.json/` mirror
generated from the official `modelcontextprotocol/specification` repository.

Generated code lives in `rust/`, `go/`, and `more/` and is committed (no
codegen at build time — keep the dev loop fast).

## Adding a new runtime

1. Create `core/mcp-idl/<lang>/` directory
2. Add code-gen step in `tools/codegen.sh`
3. Update this README

## Audit

- Spec: `phenotype-registry/ecosystem-consolidation/dossier/TIER3-P2-MCP-POLYGLOT.md`
- SSOT: `phenotype-registry/registry/disposition-index.json` PR #541
