# ADR 002: Choice of Languages

## Status
Accepted

## Context
Helios-CLI is a sophisticated build and deployment orchestration tool. It needs to support multiple platforms and integrate with various cloud providers and build systems.

## Decision
We will use a polyglot approach: **Rust** for the core CLI and critical path, **Go** for cloud integrations, and **Mojo** for high-performance computational kernels.

- **Rust**: Chosen for the primary CLI and core orchestration logic due to its performance, reliability, and excellent cross-compilation support. It ensures a fast, single-binary distribution for the CLI.
- **Go**: Chosen for cloud integrations and provider-specific modules. Go's extensive cloud-native ecosystem and ease of network programming make it ideal for this purpose.
- **Mojo**: Chosen for experimental, high-performance computational kernels where extreme speed and hardware utilization are required.

## Consequences
- **Pros**:
    - A high-performance, reliable CLI that is easy to distribute.
    - Seamless integration with cloud ecosystems using Go's libraries.
    - Ability to push the boundaries of performance with Mojo for specialized tasks.
- **Cons**:
    - Increased complexity in the build and release process (managed via Bazel).
    - Need for diverse language expertise across the team.
    - Potential friction in inter-process communication between Rust, Go, and Mojo components.
