**Work state:** ACTIVE · **Progress:** `████████░░` 8/10

HexaKit is a Rust workspace for reusable infrastructure primitives and hexagonal-architecture building blocks. It packages focused libraries for error handling, contracts, policy, telemetry, health, and adapter/port patterns so downstream systems can compose a consistent, maintainable infrastructure layer instead of duplicating foundation code.

## Usage / Quickstart

```bash
git clone https://github.com/KooshaPari/HexaKit.git
cd HexaKit
cargo metadata --format-version 1
cargo test
```

To consume a crate from this workspace, add the relevant package to your Rust project and depend on it from `Cargo.toml`.

<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/<REDACTED>/HexaKit/total?style=flat-square&label=downloads&color=blue)
![GitHub release](https://img.shields.io/github/v/release/<REDACTED>/HexaKit?style=flat-square&label=release)
![License](https://img.shields.io/github/license/<REDACTED>/HexaKit?style=flat-square)
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
| Open issues | 4 |
| Open PRs | 2 |
| Focus | hexagonal-ports kit (46 crates) — phenoObservability consumer |

Progress: ████████░░ 80%

> **Work state:** ACTIVE · **Progress:** `██████░░░░ 60%`
> Canonical org hexagonal-ports kit — 46 workspace crates (errors/event-bus/ports-canonical/core/policy/telemetry/...); workspace resolves (cargo metadata ✓), consumed live by phenoObservability via git dep · updated 2026-06-02

> **Pinned references (Phenotype-org)**
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: AGENTS.md

# phenotype-infrakit — Phenotype Infrastructure Kit

## Quickstart

> Phenotype-org hexagonal architecture toolkit

```bash
# Clone, build, test
git clone https://github.com/KooshaPari/HexaKit.git
cd HexaKit
```

```rust
// Add to Cargo.toml:
// hexakit = "<version>"
```

See [SPEC.md](SPEC.md) for the full specification and [llms.txt](llms.txt) for machine-readable metadata.


**HexaKit** is the GitHub repository name for **phenotype-infrakit**, the Phenotype Infrastructure Kit.

This is a **Rust workspace** containing 16+ specialized infrastructure libraries for building scalable, maintainable systems. It includes cross-cutting concerns like error handling, caching patterns, contract-based design, health checks, policy evaluation, and hexagonal architecture port/adapter patterns — not multi-language template scaffolding.

## What is a shelf?

A shelf is an organizational layer above individual projects. Think of it like
`~/code/` or `/opt/` — a directory containing related but independent repositories.
Each project is a standalone git repo; the shelf is their shared home.

## Quick Start

### Finding a project
```bash
find . -maxdepth 1 -mindepth 1 -type d | sort   # Top-level project directories
cat README.md                                  # Shelf overview and navigation
```

### Working on a project
```bash
cd <project-name>      # e.g., cd heliosCLI
git status             # Verify you're in the right place
```

### Creating a worktree
```bash
git worktree add .worktrees/my-feature -b my-feature
cd .worktrees/my-feature
```

## Project Categories

Projects are organized into functional categories at the top level:

| Category | Contents |
|----------|----------|
| `apps/` | User-facing applications |
| `tooling/` | Developer tools, CLIs, scripts |
| `infra/` | Infrastructure, deployment, devops |
| `libs/` | Shared libraries and packages |
| `platforms/` | Platform-as-product projects |

Note: Not all projects are yet in these categories — the reorganization is ongoing.
Use the top-level directory listing and each project's `README.md` or `AGENTS.md` as the
authoritative source.

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Shelf overview and navigation |
| `AGENTS.md` | Agent interaction rules |
| `GOVERNANCE.md` | Shelf governance |
| `CLAUDE.md` | Claude Code settings |
| `STATUS.md` | Current shelf status |
| `CHANGELOG.md` | Shelf change history |

## Architecture

```
repos/                          # ← Shelf root (YOU ARE HERE)
├── .worktrees/                 # Worktree staging area
├── .archive/                    # Archived projects
├── .claude/                     # Shelf-level Claude settings
├── .cursor/                     # Shelf-level Cursor settings
├── projects/                    # Project metadata & catalog
├── docs/                        # Cross-project documentation
│   ├── adr/                   # Architecture Decision Records
│   └── guides/                # How-to guides
├── scripts/                     # Cross-project scripts
├── governance/                  # Governance tooling
├── plans/                       # Work plans
└── [projects]                   # ~30 independent git repos
```

## Agent Workflow

1. **Identify the project** - Check the target project's `README.md` or ask the user
2. **Navigate to project** — `cd <project-name>`
3. **Read project rules** — Check for `CLAUDE.md` or `AGENTS.md` in project
4. **Do the work** — Follow shelf rules in `AGENTS.md`
5. **Commit & push** — Use conventional commits, open PR if needed

## NOT AgilePlus

This shelf contains **many projects**, of which AgilePlus is one.
AgilePlus-specific documentation lives inside the `AgilePlus/` project directory,
not at shelf level.

The files that were previously here describing AgilePlus have been moved to
their correct locations:
- AgilePlus governance → `AgilePlus/GOVERNANCE.md`
- AgilePlus agent rules → `AgilePlus/AGENTS.md`
- AgilePlus README → `AgilePlus/README.md`

## Getting Help

- Shelf-level issues: Ask here
- Project-specific issues: `cd <project>` and check that project's docs
- Architecture decisions: `cat docs/adr/INDEX.md` or inspect `docs/`
- General questions: Check this `README.md` and the target project's `README.md` first

---

## Rich Media Stubs

<!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="HexaKit quickstart — scaffold a new project from template" journey="" status="TODO" -->
> **[RICH MEDIA PLACEHOLDER]** *Annotated screenshot of the terminal after running the HexaKit scaffold command.*
<!-- END-RICH-MEDIA-STUB -->

<!-- RICH-MEDIA-STUB type="recording-gif" subject="Template browser — browsing and selecting a scaffold template" journey="" status="TODO" -->
> **[RICH MEDIA PLACEHOLDER]** *GIF of browsing available templates and scaffolding a new project.*
<!-- END-RICH-MEDIA-STUB -->

<!-- RICH-MEDIA-STUB type="recording-mp4" subject="Template authoring — creating a new HexaKit template" journey="" status="TODO" -->
> **[RICH MEDIA PLACEHOLDER]** *Video of authoring a new template and publishing it to the HexaKit registry.*
<!-- END-RICH-MEDIA-STUB -->

<!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="HexaKit architecture — template registry + scaffold engine diagram" journey="" status="TODO" -->
> **[RICH MEDIA PLACEHOLDER]** *Annotated component diagram of HexaKit scaffold engine and template registry.*
<!-- END-RICH-MEDIA-STUB -->
