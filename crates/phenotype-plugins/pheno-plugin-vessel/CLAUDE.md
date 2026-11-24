# phenotype-vessel

Rust container utilities library. Provides Docker, Podman, and containerd abstractions for building, running, and managing containers.

## Stack
- Language: Rust
- Key deps: Cargo, tokio (async), docker API client

## Structure
- `src/`: Rust library
  - `client.rs`: Unified container client (Docker/Podman/containerd)
  - `image.rs`: Image build and pull operations
  - `container.rs`: Container lifecycle management
  - `compose.rs`: Multi-container orchestration

## Key Patterns
- Trait-based abstraction over multiple container runtimes
- Async-first (tokio); all I/O operations are async
- Errors are typed and explicit — no silent failures

## Adding New Functionality
- New container runtime: implement the `ContainerRuntime` trait in `src/`
- New operations: extend the client modules
- Run `cargo test` to verify
