# Sidekick Consolidation Notes

## Overview

Sidekick bootstrap consolidates 4 agent micro-utility repos into a named Rust workspace collection. Each sub-crate is independently consumable; workspace structure enables shared CI/CD, unified versioning, and grouped documentation.

## Source → Target Mapping

| Source Repo | Target Crate | Purpose | Status |
|-------------|--------------|---------|--------|
| `agent-user-status` | `crates/sidekick-presence` | User presence and focus-mode tracking | ✅ Copied |
| `thegent-dispatch` | `crates/sidekick-dispatch` | Multi-provider agent dispatch router | ✅ Copied |
| `cheap-llm-mcp` | `crates/sidekick-cheap-llm` | Budget LLM routing via FastMCP (Python) | ✅ Copied |
| `agent-imessage` | `crates/sidekick-messaging` | Multi-provider messaging (iMessage/SMS/RCS) | ⏸️ Not found; stub pending |

## Why Consolidate?

1. **Unified dependency management**: Shared workspace Cargo.toml eliminates version skew
2. **Grouped documentation**: Single README explains all 4 components
3. **Simplified CI/CD**: One workflow builds/tests all crates
4. **Easier publishing**: crates.io prefix `sidekick-*` groups them visually
5. **Clear ownership**: Sidekick namespace signals "agent infrastructure" explicitly

## Polyglot Design

- **Rust crates**: sidekick-presence, sidekick-dispatch (compiled binaries + libraries)
- **Python sub-package**: sidekick-cheap-llm (FastMCP wrapper)
  - Integrates via workspace pyproject.toml (future)
  - Callable from Rust via subprocess or Python FFI if needed

## Cutover Plan

1. **Verification phase** (current): Workspace builds, tests pass, no blocker issues
2. **User approval**: Confirm crates copied correctly, naming acceptable
3. **Switchover**: Update all import paths across Phenotype org to reference `sidekick-*` crates
4. **Archive originals**: Move 4 source repos to `.archive/` once integration confirmed

## Known Gaps

- **sidekick-messaging**: `agent-imessage` source not located; likely embedded in MCP system
  - Resolution: Either locate source or stub integration point for future
- **Python integration**: `sidekick-cheap-llm` workspace pyproject.toml not yet created
  - Resolution: Create after Rust crates verified

## Version Strategy

- Bootstrap at **v0.0.1** (development)
- Transition to SemVer once integration complete (v0.1.0 → v1.0.0 based on API stability)
- Each crate can be released independently if needed (e.g., security patch to sidekick-presence)

## Next Steps

1. User reviews consolidation notes
2. Approve naming and structure
3. CI/CD: Set up GitHub Actions workflow (build, test, publish)
4. Migrate all imports across Phenotype (AgilePlus, HeliosCLI, etc.) to `sidekick-*`
5. Archive source repos after confirmation
