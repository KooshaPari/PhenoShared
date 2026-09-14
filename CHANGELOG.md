# Changelog

All notable changes to NanoVMS will be documented in this file.

Format follows [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added
- Production Dockerfile with multi-stage build, non-root user, healthcheck
- docker-compose.yml with security hardening and persistent volumes
- INSTALL.md with Docker, source, go install, and CLI documentation
- SECURITY.md with threat model, CVE process, and security checklist
- ADR index updated with all 15 architecture decision records
- BytePort cross-ecosystem contract tests

### Changed
- Fixed registry.go comment to reflect actual 30-tier count (was 15)
- Updated ADR-015 with portfolio boundary audit findings

## [0.3.0] - 2026-09-09

### Added
- `thegent-nvms` FFI bindings (migrated from PhenoCompose)
- Snapshot store interface and memory implementation
- Real Prometheus metrics collector
- Criterion benchmarks for FFI, tier selection, and adapter registry
- Real adapter E2E tests for native, gVisor, and Docker
- gVisor + native tier real execution integration tests

### Fixed
- Reject unimplemented KVM guest lifecycle (tier policy)
- Suppressed gosec G304 and G204 findings with nosec annotations
- Addressed golangci-lint findings in metrics and orchestrate packages

## [0.2.0] - 2026-08-15

### Added
- Multi-tier sandbox orchestration engine (30 tiers)
- Hexagonal architecture with pluggable adapters
- CLI with `nvms run`, `nvms list`, `nvms stop`, `nvms probe`
- API server with Bearer token authentication
- Tier policy engine for automated isolation selection
- Platform-specific adapters (Linux, macOS, Windows)
- Docker, gVisor, Firecracker, Podman, LXC adapters
- Rate limiting middleware
- Resilience patterns (retry, circuit breaker)

## [0.1.0] - 2026-07-01

### Added
- Initial project scaffold
- Go module setup with hexagonal architecture
- Basic sandbox interface definitions
- CI/CD pipeline with GitHub Actions
