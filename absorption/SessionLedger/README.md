# zz-pause

Long pause. No active development. Code preserved.

---

# SessionLedger

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/KooshaPari/SessionLedger/badge)](https://securityscorecards.dev/viewer/?uri=github.com/KooshaPari/SessionLedger)

[![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net) [![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/KooshaPari/SessionLedger/total)](https://github.com/KooshaPari/SessionLedger/releases)

<p align="center">
  <a href="assets/brand/sessionledger-icon.svg"><img src="assets/brand/sessionledger-icon.svg" alt="SessionLedger" width="160" height="160"></a>
</p>
<p align="center"><em>OKF-native session compiler — capture, archive, replay AI agent sessions losslessly.</em></p>
<p align="center"><sub>Lab-Coat palette · <a href="assets/brand/README.md">brand assets &amp; tokens</a> · OKF v1.0 spec · <a href="docs/assets/identity/">visual identity demo</a></sub></p>

---

> Capture, archive, and replay your AI sessions. OKF-native session compiler.

## Features

- **sl-daemon**: HTTP API — bundle ingest, search, replay SSE, metrics
- **sl-viewer**: Dioxus desktop app with Timeline, Search, Replay, LiveFeed tabs
- **OKF validation**: POST /api/ingest validates bundle schema
- **Archive/restore**: gzip-compressed archival with flate2
- **Filter flags**: --since, --until, --model, --min-tokens, --tag, --limit
- **Dark/light theme**: Lab-Coat #2563eb accent, #14b8a6 secondary
- **Startup banner**: colored ANSI branding

## Install

Portable `sl-viewer` from [GitHub Releases](https://github.com/KooshaPari/SessionLedger/releases)
(checksum-verified):

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
```

```powershell
# Windows (PowerShell)
irm https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.ps1 | iex
```

Pin a tag with `SL_VERSION=v0.1.0`. Review the script before piping it to a shell.

Daemon / CLI from Git (developers):

```bash
cargo install --git https://github.com/KooshaPari/SessionLedger --locked --path crates/sl-daemon
```

Homebrew and winget manifests live under [`packaging/homebrew`](packaging/homebrew)
and [`packaging/winget`](packaging/winget) (tap / winget-pkgs publish next). Channel
status: [`packaging/channels.md`](packaging/channels.md).

## Quick Start

```
just dev
# or: task dev
# or: make dev
# or separately:
cargo run -p sl-daemon -- serve
cargo run -p sl-viewer
```

## API

| Endpoint     | Description |
| ------------ | ----------- |
| GET /healthz | Liveness    |

Optional Langfuse-compatible OTLP tracing is disabled by default. See
`crates/sl-daemon/README.md` for the opt-in environment contract and privacy
boundaries.
| GET /api/bundles | List bundles |
| GET /api/search | Filter bundles |
| GET /api/metrics | Session statistics |
| GET /api/replay/:id | SSE replay |
| POST /api/ingest | Validate + ingest |

## Deploy

```
podman build -t sl-daemon .
podman run -v sl-data:/data -p 8080:8080 sl-daemon
```