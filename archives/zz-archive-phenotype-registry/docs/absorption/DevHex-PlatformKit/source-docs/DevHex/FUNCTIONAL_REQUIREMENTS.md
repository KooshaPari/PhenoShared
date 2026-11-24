# Functional Requirements

## Overview
DevHex provides a hexagonal Go abstraction for development environment backends.
It exposes a single `Environment` port, a backend registry, and adapter
implementations for Docker, Podman, Nix, and native process execution.

## Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Core port abstraction | Provide the `Environment` interface and backend registry as the stable public abstraction for consumers. | High | Implemented |
| FR-002 | Environment lifecycle operations | Support `Start`, `Stop`, `Status`, `Exec`, and `Logs` operations through the port interface. | High | Implemented |
| FR-003 | Pluggable backend adapters | Provide adapter implementations for Docker, Podman, Nix, and native process execution. | High | Partial |
| FR-004 | Structured environment configuration | Support configuration for ports, volumes, environment variables, working directory, and status metadata. | Medium | Implemented |

## Test Traceability

| FR | Test File | Test Name | Status |
|----|-----------|-----------|--------|
| FR-001 | `tests/smoke_test.go` | `TestSmoke` | Traced |
| FR-002 | `tests/smoke_test.go` | `TestSmoke` | Partial |
| FR-003 | `tests/smoke_test.go` | `TestSmoke` | Pending |
| FR-004 | `tests/smoke_test.go` | `TestSmoke` | Pending |

## Coverage Notes

- `tests/smoke_test.go` is the only current test entrypoint and only verifies
  basic package structure.
- Adapter-specific behavior still needs dedicated tests before the traceability
  matrix can be considered complete.
