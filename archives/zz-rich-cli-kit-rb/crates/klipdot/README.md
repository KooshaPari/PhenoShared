<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/KlipDot/total?style=flat-square&label=downloads&color=blue)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/KlipDot?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/KlipDot?style=flat-square)
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
<!-- work-state: Phase 3 spec+test+trace added -->
[████████░░] 80% — spec+test+trace layer

# KlipDot — Terminal Image Interception Framework (Archived)

> **Work state:** PHASE 3 (Spec + Test + Traceability)  
> Updated 2026-06-15 — Phase 3 spec layer added (docs/specs/FR.md, docs/specs/TRACEABILITY.md)


[![License](https://img.shields.io/github/license/KooshaPari/KlipDot)](LICENSE)

**ARCHIVED PROJECT - DO NOT DELETE OR UNARCHIVE**  
*Historical Reference: Universal Terminal Image Capture & Interception Research*

KlipDot was a Rust-based research project exploring AI-driven desktop integration through universal image capture and real-time clipboard interception for CLI/TUI applications. Preserved for historical reference and architectural research purposes only.

## Status

**Status**: ARCHIVED (2024-Q1)  
**Reason**: Superseded by browser automation (bare-cua) and modern sandbox approaches  
**Maintenance**: Historical reference only — no active development

## Original Purpose & Design

KlipDot investigated daemon-based terminal image interception as a foundation for AI agent integration with legacy CLI/TUI tools. It provided:
- Universal image capture for any terminal application
- Real-time clipboard monitoring and event streaming
- Terminal image preview rendering (chafa/timg)
- HTTP API for AI service integration
- Cross-platform shell integration (ZSH, Bash, Fish)

**Architecture**: Lightweight daemon running in background, listening on socket for capture requests, streaming to HTTP listeners.

## Technology Stack (Historical)

- **Language**: Rust (edition 2018)
- **Design Pattern**: Daemon-based interceptor
- **Integration**: Shell hooks, HTTP event streaming
- **Cross-platform**: macOS, Linux, Windows support

## Successor Projects & Migration Path

If you need terminal automation or device integration, use these active alternatives:
- **[bare-cua](../bare-cua)** — Headless browser automation with screenshot/interaction (recommended)
- **[KDesktopVirt](../KDesktopVirt)** — Desktop virtualization for end-to-end automation
- **[KVirtualStage](../KVirtualStage)** — Virtual display sandboxing

## Documentation & Reference

- **CLAUDE.md** — Historical development contract (archived)
- **Source Code**: Preserved as-is for research reference
- **No active PRs or issues** — read-only reference

## Governance & License

- **License**: MIT (Historical)
- **Related**: See `phenotype-shared` and `bare-cua` for modern automation primitives
- **Reuse Policy**: Code patterns may be referenced for research; do not fork or reactivate without explicit approval

---

**Archived**: 2024-Q1 | **Last Reviewed**: 2026-04-24 | **For Research Only**

## License

MIT — see [LICENSE](./LICENSE).

## Documentation

This repository includes the following cross-cutting documents:

- [`AGENTS.md`](AGENTS.md) — operating instructions for AI agents and human contributors
- [`SPEC.md`](SPEC.md) — formal specification of behavior and contracts
- [`docs/`](docs/) — design notes, ADRs, and supporting documentation (see [`docs/index.md`](docs/index.md))

