# heliosApp nanovms Session Isolation

## Meta

- **ID**: 016-heliosapp-nanovms-isolation
- **Title**: heliosApp nanovms Session Isolation — VM-Level Agent Sandboxing
- **Created**: 2026-04-04
- **State**: specified
- **Scope**: heliosApp, nanovms (cross-project integration)

## Context

heliosApp is a developer-focused AI runtime environment with a desktop shell, terminal multiplexing (Zellij/PAR), session management, and multi-provider AI inference. It uses Bun/TypeScript with a LocalBus message architecture. Currently, PTY sessions and AI provider execution run in the host process with limited isolation.

nanovms provides 3-tier isolation (WASM, gVisor, Firecracker) that could secure heliosApp's multi-user colab-renderer scenarios and isolate untrusted agent execution. This is especially valuable for:

- Multi-user collaborative sessions
- Untrusted AI agents with terminal access
- Session recovery via VM snapshots
- Cross-platform consistent isolation

## Problem Statement

heliosApp sessions lack strong isolation:

- **Shared process space**: PTY sessions run in host runtime
- **No VM boundaries**: AI providers share memory with runtime
- **Multi-user risk**: colab-renderer exposes host to other users
- **No checkpoint/resume**: Sessions can't be snapshotted
- **Platform inconsistency**: Different security on macOS vs Windows

## Goals

- Isolate heliosApp PTY sessions in nanovms sandboxes
- Isolate AI provider execution in appropriate tiers
- Enable multi-user colab-renderer with VM-level boundaries
- Session snapshot/recovery via nanovms VM capabilities
- Cross-platform: macOS (Lima), Windows (WSL2), Linux (KVM)

## Non-Goals

- Rewriting heliosApp core runtime (keep Bun/TypeScript)
- Changing LocalBus architecture (add nanovms as backend)
- Supporting non-tiered modes
- Modifying nanovms Go implementation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     heliosApp Desktop Shell                        │
│              (ElectroBun UI — tabs, panels, settings)              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ LocalBus (in-process message bus)
┌──────────────────────────▼──────────────────────────────────────┐
│                     Runtime Engine (Bun/TS)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Sessions │ │   PTY    │ │ Providers│ │ Recovery │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘          │
│       │            │            │            │                │
│  ┌────┴────────────┴────────────┴────────────┴────┐          │
│  │        nanovms Backend Adapter                   │          │
│  │  (HTTP/gRPC client to nanovms sidecar)           │          │
│  └─────────────────────┬──────────────────────────────┘          │
└──────────────────────┼──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │  Tier 1 │   │  Tier 2 │   │  Tier 3 │
   │  WASM   │   │ gVisor  │   │MicroVM  │
   │ Sandbox │   │Container│   │Firecracker
   │         │   │         │   │         │
   │ Providers│  │  PTY    │   │  Full   │
   │  Tools  │   │ Session │   │ Session │
   └─────────┘   └─────────┘   └─────────┘
```

## Integration Strategy

### Option A: nanovms Sidecar (Recommended)

- nanovms runs as separate process (Go binary)
- heliosApp communicates via HTTP/gRPC
- Clean separation, easy upgrades
- Fits Bun/TypeScript runtime model

### Option B: Shared Library

- nanovms compiled as shared lib
- Bun FFI bindings via `bun:ffi`
- Tighter coupling but lower latency
- More complex build process

### Option C: WebSocket Bridge

- nanovms exposes WebSocket API
- heliosApp connects via native WebSocket
- Good for future remote scenarios

## Tier Mapping

| heliosApp Component | nanovms Tier | Use Case |
|--------------------|--------------|----------|
| AI Provider tools | Tier 1 (WASM) | Fast tool execution |
| PTY Session | Tier 2 (gVisor) | Terminal isolation |
| colab-renderer user | Tier 3 (Firecracker) | Multi-user isolation |
| Full session | Tier 3 (microVM) | Snapshot/recovery |

## Work Packages

| WP | Title | Owner | State | Est |
|----|-------|-------|-------|-----|
| WP1 | nanovms HTTP API design | TBD | planned | 2d |
| WP2 | heliosApp nanovms adapter | TBD | planned | 4d |
| WP3 | Tier 1 provider tools | TBD | planned | 3d |
| WP4 | Tier 2 PTY session isolation | TBD | planned | 4d |
| WP5 | Tier 3 colab-renderer isolation | TBD | planned | 5d |
| WP6 | Session snapshot/recovery | TBD | planned | 3d |
| WP7 | Platform support (macOS/Win/Linux) | TBD | planned | 4d |
| WP8 | Integration tests | TBD | planned | 3d |
| WP9 | Documentation | TBD | planned | 2d |

## Acceptance Criteria

- [ ] AI provider tools can run in WASM sandbox (Tier 1)
- [ ] PTY sessions can be isolated in gVisor (Tier 2)
- [ ] colab-renderer users get Firecracker isolation (Tier 3)
- [ ] Session snapshot creates VM checkpoint
- [ ] Session recovery restores from checkpoint
- [ ] Cross-platform: macOS, Windows, Linux
- [ ] LocalBus integration works transparently
- [ ] <500ms overhead for Tier 2, <1000ms for Tier 3

## Dependencies

- nanovms HTTP API implementation
- heliosApp backend adapter pattern
- Bun FFI or HTTP client support

## Related

- worklogs/INTEGRATION.md — Cross-project integration analysis
- heliosApp AGENTS.md — Runtime architecture
- heliosApp README — LocalBus protocol details
- nanovms README — Tier specifications

## FR Traceability

| FR | Description | WP |
|----|-------------|----|
| FR-016-001 | nanovms HTTP API | WP1 |
| FR-016-002 | heliosApp adapter | WP2 |
| FR-016-003 | Tier 1 provider isolation | WP3 |
| FR-016-004 | Tier 2 PTY isolation | WP4 |
| FR-016-005 | Tier 3 colab isolation | WP5 |
| FR-016-006 | Session snapshot | WP6 |
| FR-016-007 | Cross-platform support | WP7 |
