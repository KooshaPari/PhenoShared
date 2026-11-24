# AgilePlus Desktop

The AgilePlus desktop client. **Step-1** ships as an [Electrobun][1] shell.
**End-state** (per the platform ADR) is a per-platform native client:

- **Windows:** `WinUI-rs` (Rust + WinUI 3)
- **macOS:** `SwiftUI` (Swift)
- **Linux:** native shell (GTK 4 or the platform team's choice)

Electrobun is intentionally a stopgap. It lets us ship a real desktop
UX today on every platform while the native clients are built. The
two surfaces — web and desktop — are **separate apps** with separate
release trains.

## Step-1 scope (Electrobun)

- Read/write **local repo state** in a user-selected AgilePlus repo
  (spec-kit style: `kitty-specs/`, `docs/adr/`, `traces/`, acceptance
  files).
- Drive the `agileplus` CLI for project management state transitions
  (specify, status, wp advance).
- Browse specs, ADRs, and traces; advance PM state.

## What it is NOT

- **Not online.** No network calls. The selected repo's filesystem is
  the single source of truth.
- **Not the web client.** This app does not share a runtime with the
  `agileplus-landing` / web surface. UI is hand-rolled, not a port.
- **Not the end-state native client.** When WinUI-rs / SwiftUI /
  Linux-native are ready, this directory is replaced — not evolved.

## Layout

```
desktop/
  package.json          # Electrobun app manifest
  tsconfig.json         # TS config (strict)
  electrobun.config.ts  # Step-1 build manifest
  scripts/build.mjs     # `npm run build` entry
  src/
    index.ts            # main process
    paths.ts            # resolved local paths
    repo-bridge.ts      # read/write specs, ADRs, traces
    cli.ts              # wraps the `agileplus` CLI
    views/
      index.ts          # view wrapper + RPC registration
      main.html         # renderer HTML
      main.css          # renderer styles
      main.ts           # renderer bootstrap
```

## Build (skeleton — not yet run in this PR)

```sh
cd desktop
npm install
npm run build
```

The build step is intentionally not executed in this commit — this is a
skeleton, and CI for the desktop client will be wired up alongside the
native clients in a follow-up PR.

[1]: https://electrobun.dev/
