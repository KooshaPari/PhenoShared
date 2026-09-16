# Vessel Core — Container Utilities

## Overview

Container utilities for Rust. Docker, Podman, and containerd abstractions.

## Features

### Core Operations

1. **Build** — Build container images with Dockerfile parsing
2. **Run** — Start and manage containers with lifecycle management
3. **Compose** — Multi-container orchestration
4. **Registry** — Push and pull images from registries

## Requirements

- FR-001: Docker client integration with bollard
- FR-002: Podman support via podman-api
- FR-003: Image build from Dockerfile
- FR-004: Container lifecycle management
- FR-005: Registry authentication and operations

## Architecture

```
src/
├── lib.rs              # Public API
├── docker/             # Docker adapter
├── podman/             # Podman adapter
├── builder.rs          # Image builder
├── runtime.rs          # Container runtime
├── compose.rs          # Compose file parser
└── registry.rs         # Registry client
```
