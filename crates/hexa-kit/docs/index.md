# HexaKit Documentation

Cross-repo documentation and architectural decisions for the Phenotype repos shelf.

## Project Structure

HexaKit is the repos shelf — a polyrepo containing ~30 independent projects:

```
HexaKit/
├── agileplus/          # Spec-driven development engine (Rust + Python)
├── platforms/thegent/  # Agent execution platform (Go + Python + TS)
├── heliosCLI/          # CLI agent harness (Rust)
├── crates/             # phenotype-* Rust foundation crates
├── kits/               # Language kits (HexaPy, HexaGo, HexaType, ...)
├── templates/          # Project templates
├── harnesses/          # Agent harness documentation
├── kitty-specs/        # Feature specifications (27 specs)
├── docs/               # VitePress documentation site
└── worklogs/           # Agent worklogs
```

## Documentation Sections

### Getting Started

- [Quick Start Guide](./guide/quick-start.md)
- [Getting Started](./guide/getting-started.md)
- [Initialization](./guide/init.md)
- [Configuration](./guide/configuration.md)

### Core Guides

- [Workflow](./guide/workflow.md) — Main development workflow
- [Triage](./guide/triage.md) — Issue and bug triage
- [Sync](./guide/sync.md) — External system synchronization
- [Local-First Deployment](./guide/local-first-deployment.md)

### Reference

- [Traceability Map](./reference/TRACEABILITY_MAP.md)
- [Configuration Standards](./reference/CONFIGURATION_STANDARDS.md)
- [Validation Standards](./reference/VALIDATION_STANDARDS.md)
- [FR Tracker](./reference/FR_TRACKER.md)

### Architecture

- [Architecture Overview](./architecture.md)
- [ADR Index](./adr/ARCHITECTURE.md)
- [Defensive Patterns](./DEFENSIVE_PATTERNS.md)
- [LOC Reduction Opportunities](./LOC_REDUCTION_OPPORTUNITIES.md)

### Governance

- [Governance ADRs](./governance/ADR-001-external-package-adoption.md)
- [Release Governance](./kitty-specs/002-org-wide-release-governance-dx-automation/)

### Adoption

- [Crate Adoption Overview](./adoption/)
- [phenotype-config-core](./adoption/phenotype-config-core.md)
- [phenotype-error-core](./adoption/phenotype-error-core.md)
- [phenotype-health](./adoption/phenotype-health.md)
- [phenotype-logging](./adoption/phenotype-logging.md)
- [phenotype-retry](./adoption/phenotype-retry.md)

### Feature Specs

- [001: Spec-Driven Development Engine](./specs/001-spec-driven-development-engine/)
- [002: Org-Wide Release Governance](./specs/002-org-wide-release-governance-dx-automation/)
- [004: Modules and Cycles](./specs/004-modules-and-cycles/)

### Research

- [Tech Radar](./research/2026-03-29-TECH-RADAR-RESEARCH.md)
- [Local-First Tech Research](./LOCAL_FIRST_TECH_RESEARCH.md)
- [PhenoSDK Package Audit](./research/PHENOSDK_PACKAGE_AUDIT.md)

### Crate Index

| Crate | Purpose |
|-------|---------|
| `phenotype-event-sourcing` | Append-only event store with SHA-256 hash chains |
| `phenotype-cache-adapter` | Two-tier LRU + DashMap cache with TTL |
| `phenotype-policy-engine` | Rule-based policy evaluation with TOML config |
| `phenotype-state-machine` | Generic FSM with transition guards |
| `phenotype-contracts` | Shared traits and types |
| `phenotype-error-core` | Canonical error types |
| `phenotype-health` | Health check abstraction |
| `phenotype-config-core` | Configuration management |

## Quick Links

| Resource | Description |
|----------|-------------|
| [SPEC.md](../SPEC.md) | Shelf specification |
| [SOTA.md](../SOTA.md) | State of the art research |
| [ADR.md](../ADR.md) | Architecture decision records |
| [GOVERNANCE.md](../GOVERNANCE.md) | Shelf governance |
| [AGENTS.md](../AGENTS.md) | Agent interaction rules |
| [USER_JOURNEYS.md](../USER_JOURNEYS.md) | User workflows |

## Localization

Translated documentation available in:
- [فارسی (Farsi)](./fa/)
- [فارسی (Latin)](./fa-Latn/)
- [简体中文 (Simplified Chinese)](./zh-CN/)
- [繁體中文 (Traditional Chinese)](./zh-TW/)
