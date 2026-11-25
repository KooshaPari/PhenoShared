# BytePort Rust Migration Plan

## Current State (2026-06-23)
- BytePort is a **Svelte** frontend application (Node.js ecosystem)
- 71+ audit score: **L1: 1.6/9.0** (lowest in the fleet)
- Disposition: **AFFIRM → phenotype-infra** (registered in disposition-index)

## Migration Target
Full Rust backend with Svelte→Tauri migration path:
1. `byteport-ctl` CLI crate (already scaffolded in `phenotype-infra/crates/byteport-ctl/`)
2. Core infrastructure logic: service discovery, tunnel management, SSH orchestration
3. Web UI becomes optional (Tauri desktop or static WASM)

## Migration Phases

### Phase 1: Backend Extraction (Priority: HIGH)
- Port all SSH/tunnel/service logic from Svelte stores → Rust crate
- Create `byteport-core` crate with: agent_management, service_discovery, tunnel
- Keep Svelte frontend as consumer of Rust WASM or REST API

### Phase 2: CLI Tooling (Priority: MEDIUM)
- Ship `byteport-ctl` with: `init`, `connect`, `tunnel`, `status`, `logs`
- Binding to `pheno-compose` runtime for process orchestration

### Phase 3: Frontend Migration (Priority: LOW)
- Evaluate Tauri v2 for native desktop
- Fallback: keep Svelte PWA as primary UI

## Immediate Next Steps
1. Create `byteport-core` crate in `phenotype-infra/crates/`
2. Extract Svelte store logic into Rust
3. Set up WASM bindings for existing frontend
4. `cargo build` must pass before Phase 2

## Scorecard Trace
References: C-04 scorecard, L1-Delta manifest
