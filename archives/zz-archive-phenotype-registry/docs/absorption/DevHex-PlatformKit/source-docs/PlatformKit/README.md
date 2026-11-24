# PlatformKit

Unified multi-platform abstraction layer for runtime, operating system, and cloud provider interoperability across Phenotype applications.

## Overview

PlatformKit abstracts away platform-specific details (Linux, macOS, Windows, Kubernetes, cloud providers) to provide a unified interface for application code. It handles system API variations, cloud provider differences, and deployment topology concerns, allowing Phenotype applications to remain portable and configuration-driven across heterogeneous infrastructure.

## Technology Stack

- **Core**: Rust (stable, edition 2021) with async/await
- **System Integration**: libc, winapi (platform-specific)
- **Cloud SDKs**: AWS SDK (Rust), GCP auth libraries, Azure SDK
- **Container Runtime**: containerd, CRI-O interfaces
- **Configuration**: TOML/YAML with hierarchical merging
- **Async Runtime**: Tokio with multi-threaded scheduler

## Key Features

- **OS Abstraction**: Unified syscall wrapping for process, file, network, IPC
- **Cloud Provider Bridges**: Unified auth, compute, storage, secrets APIs
- **Container Integration**: Pod/container lifecycle, resource limits, networking
- **Environment Detection**: Auto-detect deployment topology (local, K8s, serverless, VM)
- **Configuration Merging**: Layered config (defaults → system → env → CLI args)
- **Process Pooling**: Cross-platform thread/process pool with work-stealing
- **Health Checks**: Liveness, readiness, startup probes with customizable backends
- **Signal Handling**: Graceful shutdown, SIGTERM/SIGINT coordination

## Quick Start

```bash
# Clone the repository
git clone https://github.com/KooshaPari/PlatformKit.git
cd PlatformKit

# Review governance and workspace setup
cat CLAUDE.md

# Build platform detection + abstraction layer
cargo build --all-features
cargo build --release

# Run platform-specific tests
cargo test --all -- --nocapture

# Feature flags for targeted builds
cargo build --no-default-features --features "unix,aws"
cargo build --no-default-features --features "windows,azure"
```

## Project Structure

```
PlatformKit/
  Cargo.toml                     # Workspace manifest
  crates/
    platformkit-core/            # OS abstraction, trait definitions
    platformkit-cloud-aws/       # AWS SDK integration, EC2/S3/Secrets
    platformkit-cloud-gcp/       # GCP integration, Compute/Storage/IAM
    platformkit-cloud-azure/     # Azure SDK integration, VMs/Blobs
    platformkit-container/       # Pod/container interfaces, CRI
    platformkit-process/         # Process pooling, IPC, signals
  platforms/
    unix/                        # Linux/macOS implementations
    windows/                     # Windows-specific code
    kubernetes/                  # K8s-targeted abstractions
  examples/
    detect_topology.rs           # Auto-detect deployment context
    cross_platform_fs.rs         # Unified file system operations
  tests/
    integration/
      test_cloud_auth.rs         # Multi-cloud auth verification
      test_container_runtime.rs  # Container lifecycle tests
```

## Related Phenotype Projects

- **[PhenoDevOps](../PhenoDevOps/)** — Deployment orchestration consuming PlatformKit abstractions
- **[phenotype-infrakit](../phenotype-infrakit/)** — Infrastructure definition; uses PlatformKit for IaC drivers
- **[cloud](../cloud/)** — Multi-tenant platform; built on PlatformKit primitives

## Feature Flags

Control platform-specific compilation:

```toml
[dependencies]
platformkit = { path = ".", features = ["unix", "aws", "kubernetes"] }
```

| Flag | Platforms | Dependencies |
|------|-----------|--------------|
| `unix` | Linux, macOS | libc |
| `windows` | Windows | winapi |
| `aws` | All (optional) | aws-sdk-rust |
| `gcp` | All (optional) | gcloud-auth |
| `azure` | All (optional) | azure-sdk |
| `kubernetes` | All (optional) | kube-rs |
| `full` | All | All optional deps |

## Development

```bash
# Build with all features
cargo build --all-features --release

# Cross-compile for Windows (from macOS/Linux)
cargo build --release --target x86_64-pc-windows-gnu

# Run tests on all platforms
cargo test --all -- --nocapture
```

## Related Phenotype Projects

- **[PhenoDevOps](../PhenoDevOps/)** — Deployment orchestration consuming PlatformKit
- **[phenotype-infrakit](../phenotype-infrakit/)** — IaC definitions leveraging PlatformKit drivers
- **[cloud](../cloud/)** — Multi-tenant platform built on PlatformKit primitives

## Governance & Contributing

- **CLAUDE.md** — Workspace conventions, feature flag policies
- **Architecture Decisions**: [docs/adr/](docs/adr/)
- **API Reference**: [docs/reference/](docs/reference/)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

For testing requirements, spec traceability, and CI gates, see [AGENTS.md](AGENTS.md).

## License

MIT — see [LICENSE](./LICENSE).
