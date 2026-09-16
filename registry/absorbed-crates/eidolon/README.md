<!-- work-state: Phase 3 spec+test+trace -->
[████████░░] 80% — spec+test+trace layer
<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/Eidolon/total?style=flat-square&label=downloads&color=blue)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/Eidolon?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/Eidolon?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.
<!-- AI-DD-META:END -->
## Work State

| Field | Value |
|---|---|
| Last commit | 2026-06-08 |
| Open issues | 6 |
| Open PRs | 4 |
| Focus | desktop cross-platform stubs |

Progress: ████████░░ 80%

> **Pinned references (Phenotype-org)**
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: phenotype-org-governance/SUPERSEDED.md

# Eidolon

![Eidolon Logo](assets/logo.svg)

[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.83+-orange.svg?logo=rust&logoColor=white)](Cargo.toml)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](#status)

**Eidolon** — the Phenotype device automation collection. Drive desktop, mobile, and sandboxed environments with a unified trait-based API.

## Install

**From repository root:**
```bash
cargo build --workspace
cargo test --workspace
```

**For individual crates:**
```bash
cargo build -p eidolon-core
cargo build -p eidolon-desktop
```

**Dependencies:** Rust 1.70+, FFmpeg (for desktop screenshots)

See `docs/EXTRACTION_PLAN.md` for platform-specific setup (kmobile, KDesktopVirt, KVirtualStage).

## Overview

Eidolon provides a modular, extensible framework for automating interactions across three platform families:

- **Desktop** (macOS, Windows, Linux) — via native APIs + FFmpeg screenshot pipeline
- **Mobile** (iOS, Android) — via XCTest + UiAutomator
- **Sandbox** (nanoVMs, Docker, KVM) — for isolated test and build environments

## Architecture

```
eidolon-core/
  ├─ traits/       DesktopAutomator, MobileAutomator, SandboxAutomator
  ├─ event/        AutomationEvent (unified audit log)
  ├─ input/        PointerInput, TextInput
  ├─ viewport/     Viewport (screen dimensions, DPI, orientation)
  └─ error/        AutomationError enum

eidolon-desktop/  DesktopClient (stub; integrates KDesktopVirt FFmpeg + security)
eidolon-mobile/   MobileClient (stub; integrates kmobile interfaces)
eidolon-sandbox/  SandboxClient (stub; integrates PlayCua, bare-cua patterns)
```

Each crate is independent — no inter-crate dependencies. Implementations inherit the trait interface from `eidolon-core`.

## Key Features

- **Unified Trait Interface** — Single async API across desktop, mobile, and sandbox platforms
- **Multi-Platform Support** — macOS, Windows, Linux (desktop); iOS, Android (mobile); Docker, nanoVMs, KVM (sandbox)
- **Native APIs** — FFmpeg for desktop screenshots, XCTest for iOS, UiAutomator for Android
- **Audit Logging** — Every automation event (click, swipe, text input) recorded with timestamp and context
- **Error Handling** — Typed AutomationError enum with recovery suggestions
- **Viewport Awareness** — Automated DPI detection and orientation handling
- **Modular Design** — Use only platform-specific crates (e.g., `eidolon-desktop` without mobile deps)
- **Integration Points** — Pluggable implementations for agent orchestration, CI/CD pipelines, and testing frameworks

## Status

**Active Development** — Core trait definitions complete; platform-specific implementations in progress.

- ✓ eidolon-core trait definitions
- ✓ eidolon-desktop stub (integrates KDesktopVirt FFmpeg + security)
- ✓ eidolon-mobile stub (integrates kmobile interfaces)
- ✓ eidolon-sandbox stub (integrates KDesktopVirt + PlayCua patterns; KVirtualStage merged into KDesktopVirt 2026-04-04)
- WIP: Full desktop implementation (FFmpeg integration)
- WIP: Full mobile implementation (XCTest + UiAutomator adapters)
- WIP: Full sandbox implementation (Docker + nanoVMs drivers)

## Platform Support Matrix

> Eidolon is a **library-only** crate — there is no operator-facing CLI or HTTP service.
> Platform support below refers to where the trait implementations run, not a hosted service.

| Platform | Crate | Status | Notes |
|---|---|---|---|
| macOS (13+) | `eidolon-desktop` | Stub / in-progress | Native `CGEvent` + FFmpeg screenshot pipeline (KDesktopVirt Phase 2) |
| Windows (10+) | `eidolon-desktop` | Roadmap | `SendInput` / DXGI capture — see `docs/EXTRACTION_PLAN.md` Phase 2 |
| Linux (X11/Wayland) | `eidolon-desktop` | Roadmap | `xdotool` / `wlroots` — see `docs/EXTRACTION_PLAN.md` Phase 2 |
| iOS (16+) | `eidolon-mobile` | Stub / in-progress | XCTest bridge (kmobile Phase 1) |
| Android (API 29+) | `eidolon-mobile` | Roadmap | UiAutomator2 — see `docs/EXTRACTION_PLAN.md` Phase 1 |
| Docker | `eidolon-sandbox` | Stub (loudly fails) | `StubDockerOrchestrator` returns explicit errors until Phase 2 lands |
| nanoVMs / KVM | `eidolon-sandbox` | Roadmap | KVirtualStage patterns — see `docs/EXTRACTION_PLAN.md` Phase 3 |
| PlayCua (dispatcher) | `eidolon-sandbox` | Available | `PlayCuaDispatcher` + `PlayCuaPort` trait; inject real transport at composition time |

**Stub vs Roadmap:** _Stub_ means the crate exists with a trait skeleton and no-op or loudly-failing impls.
_Roadmap_ means the platform is intended but the crate does not even contain a skeleton yet.
Callers that hit a stub should receive a descriptive `PhenoError::Internal` or `DockerUnimplemented`
error — not silent zeros. File an issue if a stub silently succeeds without performing real work.

## Release Registry

See `release-registry.toml` for version metadata, stability information, and sub-crate status. The master index of all Phenotype collections is at `../phenotype-collections.toml`.

Schema documentation: `docs/governance/release_registry_schema.md`

## Building

```bash
cargo build --workspace
cargo test --workspace
cargo clippy --workspace -- -D warnings
```

## Traits

### DesktopAutomator

Automate desktop environments with pointer and text input.

```rust
pub trait DesktopAutomator: Send + Sync {
    async fn get_viewport(&self) -> Result<Viewport>;
    async fn screenshot(&self, path: &str) -> Result<()>;
    async fn pointer(&self, event: &PointerInput) -> Result<()>;
    async fn text(&self, event: &TextInput) -> Result<()>;
    async fn record_event(&self, event: AutomationEvent) -> Result<()>;
}
```

### MobileAutomator

Automate mobile devices with tap, swipe, and text input.

```rust
pub trait MobileAutomator: Send + Sync {
    async fn get_viewport(&self) -> Result<Viewport>;
    async fn screenshot(&self, path: &str) -> Result<()>;
    async fn tap(&self, x: i32, y: i32) -> Result<()>;
    async fn swipe(&self, x1: i32, y1: i32, x2: i32, y2: i32) -> Result<()>;
    async fn input_text(&self, text: &str) -> Result<()>;
    async fn record_event(&self, event: AutomationEvent) -> Result<()>;
}
```

### SandboxAutomator

Automate sandboxed environments with execution and resource monitoring.

```rust
pub trait SandboxAutomator: Send + Sync {
    async fn get_metadata(&self) -> Result<SandboxMetadata>;
    async fn start(&self) -> Result<()>;
    async fn stop(&self) -> Result<()>;
    async fn exec(&self, cmd: &str) -> Result<String>;
    async fn resource_usage(&self) -> Result<ResourceUsage>;
    async fn record_event(&self, event: AutomationEvent) -> Result<()>;
}
```

## Events

All automation operations are recorded as `AutomationEvent` for audit, playback, and debugging.

```rust
pub struct AutomationEvent {
    pub id: String,                   // Unique identifier
    pub event_type: String,           // "pointer", "text", "screenshot"
    pub platform: String,             // "desktop", "mobile", "sandbox"
    pub payload: EventPayload,        // Serializable input/output
    pub timestamp: u64,               // Unix seconds
}
```

## Cross-Collection Integration

Eidolon is part of the **Phenotype named collections**:

- **Sidekick** — Agent dispatch & presence
- **Eidolon** (this) — Device automation
- **Observably** — Distributed tracing & observability
- **Stashly** — State, events, caching, migrations
- **Paginary** — Knowledge collection (specs, tutorials, handbooks)

### Event Bus

Eidolon uses a shared event bus for cross-collection communication. For example, when Sidekick dispatches a task to an agent, Eidolon can subscribe to dispatch events and automate the task execution:

```rust
use phenotype_bus::{Bus, Event};

// Subscribe to Sidekick's dispatch events
let dispatch_bus = Bus::<DispatchStarted>::new(100);
let mut rx = dispatch_bus.subscribe();

while let Ok(dispatch_event) = rx.recv().await {
    // Trigger desktop/mobile/sandbox automation
    automator.screenshot("./before.png").await?;
    automator.pointer(&click_input).await?;
    automator.screenshot("./after.png").await?;
}

// Emit completion event for Observably to trace
let completion_bus = Bus::<AutomationCompleted>::new(100);
completion_bus.publish(AutomationCompleted { /* ... */ }).await?;
```

See `docs/worklogs/README.md` and `docs/worklogs/GOVERNANCE.md` for local integration context.

## Extraction Plan

See `docs/EXTRACTION_PLAN.md` for per-source-repo (KDesktopVirt, kmobile, PlayCua, bare-cua) extraction targets and salvageable modules. KVirtualStage was merged into KDesktopVirt 2026-04-04; eidolon-sandbox now integrates KDesktopVirt directly.

## Architecture Decision Record

See `docs/ADR-001-trait-based-core.md` for rationale: fresh design (trait-first) vs. direct code merge from sibling projects.

## REST API examples

The Eidolon daemon (`eidolon-daemon`) exposes the trait surface as HTTP at `/v1/`.
Sessions, devices, and automation events are first-class resources; all requests
require a bearer token; all list endpoints use cursor pagination; all mutating
endpoints accept `Idempotency-Key`; all errors follow
[RFC 7807 problem+json][rfc7807] (see
[`docs/conventions/rest-api.md`][convention] for the full contract).

### List active sessions (cursor pagination)

```bash
curl -sS https://eidolon.phenotype.dev/v1/sessions?limit=50 \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "data": [
    {"id": "sess_01HXY...", "platform": "desktop", "state": "running", "started_at": 1719000000},
    {"id": "sess_01HXZ...", "platform": "sandbox", "state": "stopped", "started_at": 1718996400}
  ],
  "next_cursor": "eyJpZCI6InNlc3NfMDFIWFoifQ",
  "has_more": false
}
```

### Open a new sandbox session (idempotent)

```bash
curl -sS https://eidolon.phenotype.dev/v1/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: 8d2e3a40-1f23-4f10-9b1f-3a8b8c0e1d22" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "platform": "sandbox",
    "image": "phenotype/sandbox-default:1.4.2",
    "resources": {"cpu": 2, "memory_mb": 4096}
  }'
```

```http
HTTP/2 201 Created
Location: /v1/sessions/sess_01HXY...
Content-Type: application/json
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
X-RateLimit-Reset: 1719005460
```

```json
{
  "id": "sess_01HXY...",
  "platform": "sandbox",
  "state": "running",
  "image": "phenotype/sandbox-default:1.4.2",
  "started_at": 1719000000
}
```

### Record a desktop pointer event (idempotent)

```bash
curl -sS https://eidolon.phenotype.dev/v1/sessions/sess_01HXY/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: 9d3f4a51-2a34-5g21-ac2g-4b9c9d1f2e33" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "event_type": "pointer",
    "payload": {"x": 412, "y": 318, "button": "left", "click_count": 1}
  }'
```

```json
{"id": "evt_01HXZ...", "recorded_at": 1719000123}
```

### Handle an RFC 7807 rate-limit error

```bash
curl -sS -i https://eidolon.phenotype.dev/v1/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST -d '{}'
```

```http
HTTP/2 429 Too Many Requests
Content-Type: application/problem+json
Retry-After: 60
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719005460
```

```json
{
  "type": "https://phenotype.dev/probs/rate-limited",
  "title": "Too Many Requests.",
  "detail": "Standard tier limit (1000/60s) reached. Retry after 60 seconds.",
  "instance": "/v1/sessions",
  "status": 429,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

[rfc7807]: https://www.rfc-editor.org/rfc/rfc7807
[convention]: https://github.com/KooshaPari/phenotype-apps/blob/main/docs/conventions/rest-api.md

## See Also

Explore Eidolon and other Phenotype collections in the [Phenotype GitHub org](https://github.com/KooshaPari).

**Sibling Collections:**
- **[Sidekick](../Sidekick)** — AI-powered agent framework & dispatch routing
- **[Stashly](../Stashly)** — Storage & persistence (caching, event sourcing, state machines)
- **[Observably](../PhenoObservability)** — Observability & distributed tracing
- **[Paginary](../Paginary)** — Knowledge collection (specs, tutorials, handbooks)
- **[phenotype-shared](../phenoShared)** — Rust infrastructure toolkit (domain, application, ports)

## License

MIT — see [LICENSE](./LICENSE).
