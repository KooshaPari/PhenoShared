# PRD — Settly

## Overview

`Settly` is a universal configuration management framework for Rust, following hexagonal architecture principles. It provides layered configs, validation, and environment support.

## Goals

- Provide a unified configuration management interface
- Support multiple config sources (files, env vars, CLI args)
- Layer configurations with proper priority handling
- Validate configurations with schema support
- Environment-specific overrides

## Epics

### E1 — Configuration Sources
- E1.1 Support TOML, YAML, JSON config files
- E1.2 Support environment variable overrides
- E1.3 Support CLI argument injection
- E1.4 Support remote config (future)

### E2 — Layering System
- E2.1 Define layer priority system (default < env < CLI)
- E2.2 Merge layered configs with deep merge
- E2.3 Detect and report conflicts

### E3 — Validation
- E3.1 JSON Schema validation support
- E3.2 Custom validator functions
- E3.3 Detailed validation error reporting

### E4 — Integration
- E4.1 Serde serialization/deserialization
- E4.2 Type-safe config access
- E4.3 Hot reload support

## Acceptance Criteria

- Config can be loaded from multiple sources
- Layer priorities work correctly
- Validation catches invalid configs
- Error messages are clear and actionable
