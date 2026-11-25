---
name: byteport-ops
description: Use for BytePort development and ops — a cross-platform data-transport app with a Go backend and a Tauri desktop client. Covers building/running the backend + desktop app, the release bundle (msi/dmg/appimage/deb), and architecture orientation.
---

# BytePort operations skill

## When to invoke
Use when working on BytePort: building or running the Go backend, the Tauri desktop client, producing release installers, or orienting in the codebase.

## Stack
- **Backend:** Go (single binary). See `go.mod`, `ARCHITECTURE.md`, `FUNCTIONAL_REQUIREMENTS.md`.
- **Desktop:** Tauri app under `frontend/web/src-tauri/` — bundles to `.msi` (Windows), `.dmg` (macOS), `.AppImage`/`.deb` (Linux).

## Build / run
- Backend: `go mod download` then `go run .` (or `go build`).
- Desktop dev: from the frontend, `bun install` then `bun run tauri dev`.
- Release installers: `bun run tauri build` (or the `release.yml` workflow on a tag) → real cross-platform installers.

## Orientation docs
`ARCHITECTURE.md`, `ADR.md`, `CHARTER.md`, `FUNCTIONAL_REQUIREMENTS.md` in the repo root.

## Notes
Ship real installers, not script launchers. Offline-first; connects to live services when needed.
