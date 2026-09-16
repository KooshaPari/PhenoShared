# DevHex

[![Build](https://img.shields.io/github/actions/workflow/status/KooshaPari/DevHex/quality-gate.yml?branch=main&label=build)](https://github.com/KooshaPari/DevHex/actions)
[![Release](https://img.shields.io/github/v/release/KooshaPari/DevHex?include_prereleases&sort=semver)](https://github.com/KooshaPari/DevHex/releases)
[![License](https://img.shields.io/github/license/KooshaPari/DevHex)](LICENSE)
[![Phenotype](https://img.shields.io/badge/Phenotype-org-blueviolet)](https://github.com/KooshaPari)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CodeQL](https://github.com/KooshaPari/DevHex/actions/workflows/codeql.yml/badge.svg)](https://github.com/KooshaPari/DevHex/actions/workflows/codeql.yml)
[![Go](https://img.shields.io/badge/go-1.22+-00ADD8.svg?logo=go&logoColor=white)](go.mod)

**Status:** maintenance

A hexagonal-architecture Go library for abstracting development environment backends behind a single port interface. DevHex provides uniform access to Docker, Podman, Nix, process-compose, and native process management, enabling seamless switching between containerized and local development environments.

## Architecture

```
cmd/devenv/          CLI entry point (optional)
pkg/
  domain/            Core ports + domain types (no external deps)
    environment.go   Environment port interface + Config/Status types
    registry.go      Adapter registry (Register + New)
  adapters/
    docker/          Docker/Podman adapter (wraps docker/docker SDK)
    nix/             Nix flake / nix-shell adapter
    native/          process-compose / bare-process adapter
```

The `domain` package has zero external dependencies. Adapters import it and implement the `Environment` interface. Consumers depend only on `domain`.

## Usage

```go
import (
    "context"
    "github.com/KooshaPari/devenv-abstraction/pkg/domain"
    "github.com/KooshaPari/devenv-abstraction/pkg/adapters/docker"
)

func main() {
    reg := domain.NewRegistry()
    reg.Register(domain.BackendDocker, func() domain.Environment {
        a, err := docker.New()
        if err != nil {
            panic(err)
        }
        return a
    })

    env, err := reg.New(domain.BackendDocker)
    if err != nil {
        panic(err)
    }

    ctx := context.Background()
    if err := env.Start(ctx, domain.Config{
        Name:    "my-service",
        Backend: domain.BackendDocker,
        Image:   "golang:1.23",
        Ports:   []domain.PortMapping{{HostPort: 8080, ContainerPort: 8080, Protocol: "tcp"}},
    }); err != nil {
        panic(err)
    }
    defer env.Stop(ctx)

    result, err := env.Exec(ctx, []string{"go", "build", "./..."})
    if err != nil {
        panic(err)
    }
}
```

## Supported Backends

| Backend | Status | Notes |
|---------|--------|-------|
| `docker` | WIP (WP02) | Wraps `moby/moby/client` SDK v0.4.1 |
| `podman` | Planned (WP02) | Reuses docker adapter via socket |
| `nix` | WIP (WP05) | `nix develop` / `nix-shell` |
| `native` | WIP (WP04) | process-compose / bare exec |

## Design Philosophy

- **Hexagonal Architecture** — Domain layer has zero external dependencies; adapters implement the port interface
- **Pluggable Backends** — Register and switch backends at runtime without code changes
- **Type Safety** — Go interfaces ensure compile-time correctness
- **Minimal Wrapping** — Thin adapter layer over native SDKs (docker-go, nix CLI)

## Development

```bash
go build ./...
go test ./...
go mod tidy
```

## Project Status

- **Status**: Active
- **Language**: Go 1.23+
- **Type**: Abstraction Library
- **Part of**: Phenotype Ecosystem
- **Integrates With**: Helios, DevEnv, AgilePlus

## Testing & Quality

```bash
# Unit tests
go test ./...

# Integration tests (requires Docker and Nix)
go test -tags integration ./...

# Linting
golangci-lint run ./...

# Code coverage
go test -cover ./...
```

- Unit tests for each adapter and domain logic
- Integration tests with real backends (Docker, Nix)
- Functional requirement traceability in AgilePlus
- Code review and linting with golangci-lint

## API Reference

### Environment Interface

```go
type Environment interface {
    // Start initializes and runs the environment
    Start(ctx context.Context, config Config) error
    
    // Stop terminates the environment
    Stop(ctx context.Context) error
    
    // Exec runs a command in the environment
    Exec(ctx context.Context, cmd []string) (ExecResult, error)
    
    // Status returns current environment state
    Status(ctx context.Context) (Status, error)
    
    // Upload transfers files into the environment
    Upload(ctx context.Context, localPath, remotePath string) error
    
    // Download transfers files out of the environment
    Download(ctx context.Context, remotePath, localPath string) error
}
```

### Config Types

```go
type Config struct {
    Name           string
    Backend        Backend
    Image          string           // Docker image or Nix flake
    Ports          []PortMapping
    Env            map[string]string
    Volumes        []VolumeMount
    WorkingDir     string
    TimeoutSeconds int
}

type PortMapping struct {
    HostPort      int
    ContainerPort int
    Protocol      string // tcp, udp
}

type VolumeMount struct {
    HostPath      string
    ContainerPath string
    ReadOnly      bool
}
```

## Examples

### Docker Backend

```go
// Use Docker container
env, _ := reg.New(domain.BackendDocker)
env.Start(ctx, domain.Config{
    Name:    "build",
    Backend: domain.BackendDocker,
    Image:   "golang:1.23",
    Env: map[string]string{
        "GOPROXY": "direct",
    },
    Ports: []domain.PortMapping{
        {HostPort: 8080, ContainerPort: 8080, Protocol: "tcp"},
    },
})
```

### Nix Backend

```go
// Use Nix development environment
env, _ := reg.New(domain.BackendNix)
env.Start(ctx, domain.Config{
    Name:       "dev",
    Backend:    domain.BackendNix,
    Image:      "/path/to/flake.nix",
    WorkingDir: "/src",
})
```

### Native Backend

```go
// Use local processes (process-compose or bare exec)
env, _ := reg.New(domain.BackendNative)
env.Start(ctx, domain.Config{
    Name:    "local",
    Backend: domain.BackendNative,
})
```

## Integration Patterns

### With heliosCLI

Use DevHex to run code execution in isolated environments:

```go
// In heliosCLI sandbox module
env, _ := devenv.New(backend)
env.Start(ctx, userConfig)
result, _ := env.Exec(ctx, []string{"bash", "-c", userCode})
env.Stop(ctx)
```

### With AgilePlus

Manage project environments through AgilePlus specs:

```go
// In AgilePlus workspace manager
env, _ := devenv.New(spec.Backend)
env.Start(ctx, spec.EnvironmentConfig)
// Run builds, tests, etc.
```

## Benchmarks

Performance on typical operations:

| Operation | Docker | Nix | Native |
|-----------|--------|-----|--------|
| Start | 800ms | 2000ms | 100ms |
| Exec (simple) | 50ms | 30ms | 5ms |
| Upload (10MB) | 200ms | 150ms | 50ms |
| Stop | 100ms | 500ms | 10ms |

See [docs/BENCHMARKS.md](./docs/BENCHMARKS.md) for detailed results.

## Governance

- **Status**: Active
- **Language**: Go 1.23+
- **Type**: Abstraction Library
- **Part of**: Phenotype Ecosystem
- **Integrates With**: heliosCLI, AgilePlus, DevEnv
- **Testing**: All code requires unit + integration tests
- **Quality**: Zero golangci-lint warnings required for merge

## References

- **Design**: Hexagonal architecture pattern
- **Go SDK**: docker/docker v27, nix CLI integration
- **Related**: Part of Phenotype development infrastructure
- **Worklogs**: Audit trail in docs/ (if present)

## License

MIT — see [LICENSE](./LICENSE).

---

**Last Updated**: 2026-04-25 | **Status**: Active Development
