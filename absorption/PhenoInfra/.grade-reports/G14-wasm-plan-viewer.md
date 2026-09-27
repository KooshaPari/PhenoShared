# G14: WASM IaC Plan Viewer — Assessment Report

**Date:** 2026-06-24
**Unit:** G14
**Type:** wasm
**Epic:** epic_G — SOTA polish & external differentiation

## Assessment

Evaluated feasibility of a WASM-based IaC plan viewer for the `iac/` workspace.

### Findings
- **Current state:** No WASM infrastructure exists in the repo
- **Rust WASM support:** The workspace uses `edition = "2024"` which has full WASM target support (`wasm32-unknown-unknown`)
- **Dependency tree:** Several deps (tokio, reqwest) have WASM-compatible features; tokio process/fs features are NOT WASM-compatible
- **Recommended approach:** Create separate `iac-plan-viewer` crate targeting `wasm32-unknown-unknown` with:
  - `serde`/`serde_json` for parsing plan JSON
  - `wasm-bindgen` for DOM rendering
  - `web-sys` for file I/O (drag-and-drop plan files)

### Recommendations
1. Create standalone viewer crate (not in workspace due to incompatible deps)
2. Use `wasm-pack` for build/publish pipeline
3. Host rendered viewer on GitHub Pages for PR review convenience

### Status
- **Phase 1:** ✅ Feasibility assessed, initial design documented
- **Phase 2:** ❌ Pending — requires dedicated WASM crate + build pipeline
