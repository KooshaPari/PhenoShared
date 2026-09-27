# ADR-001: Architecture Decision — Backend and System Architecture

**Document ID:** PHENOTYPE_BYTEPORT_ADR_001  
**Status:** Accepted  
**Last Updated:** 2026-04-03  
**Author:** Phenotype Architecture Team

---

## Table of Contents

1. [Context](#context)
2. [Decision](#decision)
3. [Consequences](#consequences)
4. [Architecture Diagrams](#architecture-diagrams)
5. [Code Examples](#code-examples)
6. [Cross-References](#cross-references)
7. [Alternatives Considered](#alternatives-considered)
8. [Implementation Notes](#implementation-notes)

---

## Context

BytePort requires a robust backend architecture capable of handling multiple concurrent concerns:

1. **NVMS Manifest Parsing**: A custom manifest format that defines application structure, services, ports, routing, and portfolio generation settings must be parsed, validated, and transformed into deployment instructions.

2. **AWS Resource Provisioning**: The system must provision AWS infrastructure (EC2, ECS, Lambda, API Gateway, security groups, VPCs) based on manifest definitions, handling the complexity of AWS APIs, credential management, and resource lifecycle.

3. **Portfolio UX Generation**: After deployment, the system must generate portfolio site components using LLM-assisted content generation, requiring integration with both cloud (OpenAI) and local (LLaMA) AI backends.

4. **CLI Interface**: Developers interact with BytePort primarily through a CLI, requiring fast startup times, clear error messages, progress indicators, and composability with shell scripts and CI/CD pipelines.

5. **Web Dashboard**: A secondary management interface for monitoring deployments, viewing service health, and managing portfolio settings.

6. **Git Integration**: The system must clone repositories, read source code, and deploy from specified branches/refs.

7. **Multi-Service Orchestration**: A single NVMS manifest can define multiple services with different ports, routes, and deployment targets, requiring coordinated provisioning and deployment.

### Constraints

- Must support AWS as the primary cloud provider (v1 scope)
- CLI must be the primary interface (per ADR-005)
- Go backend + web frontend architecture (per existing ADR-003)
- NVMS manifest format is the primary IaC definition (per existing ADR-001)
- LLM integration must support both cloud and local backends (per existing ADR-004)

### Non-Functional Requirements

- CLI startup time: <100ms
- Manifest parsing: <500ms for typical manifests
- Deployment pipeline: <135s end-to-end target
- Memory footprint: <200MB for backend process
- Concurrent deployments: Support 5+ simultaneous deployments

---

## Decision

We adopt a **modular Go backend architecture** with the following structure:

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      BytePort Backend Architecture               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Entry Points                           │  │
│  │                                                           │  │
│  │  ┌──────────────┐         ┌──────────────────────────┐   │  │
│  │  │  CLI (Cobra) │         │  HTTP Server (Gin)       │   │  │
│  │  │  byteport    │         │  :8080                   │   │  │
│  │  │  deploy      │         │  REST API                │   │  │
│  │  │  status      │         │  WebSocket (live status) │   │  │
│  │  │  list        │         │                          │   │  │
│  │  └──────┬───────┘         └────────────┬─────────────┘   │  │
│  │         │                              │                 │  │
│  │         └──────────────┬───────────────┘                 │  │
│  │                        │                                 │  │
│  └────────────────────────┼─────────────────────────────────┘  │
│                           │                                    │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │                    Service Layer                         │  │
│  │                                                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  Manifest    │  │  Deploy      │  │  Portfolio   │   │  │
│  │  │  Service     │  │  Service     │  │  Service     │   │  │
│  │  │              │  │              │  │              │   │  │
│  │  │  • Parse     │  │  • Provision │  │  • Generate  │   │  │
│  │  │  • Validate  │  │  • Deploy    │  │  • Template  │   │  │
│  │  │  • Transform │  │  • Monitor   │  │  • Publish   │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │  │
│  │         │                 │                  │           │  │
│  └─────────┼─────────────────┼──────────────────┼───────────┘  │
│            │                 │                  │              │
│  ┌─────────▼─────────────────▼──────────────────▼───────────┐  │
│  │                    Infrastructure Layer                   │  │
│  │                                                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  AWS         │  │  Git         │  │  LLM         │   │  │
│  │  │  Client      │  │  Client      │  │  Backend     │   │  │
│  │  │              │  │              │  │              │   │  │
│  │  │  • EC2       │  │  • Clone     │  │  • OpenAI    │   │  │
│  │  │  • ECS       │  │  • Read      │  │  • LLaMA     │   │  │
│  │  │  • Lambda    │  │  • Parse     │  │  • Fallback  │   │  │
│  │  │  • API GW    │  │              │  │              │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Data Layer                             │  │
│  │                                                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  SQLite      │  │  File Store  │  │  Cache       │   │  │
│  │  │  (dev)       │  │  (artifacts) │  │  (in-memory) │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Package Structure

```
backend/
├── byteport/                    # Core deployment engine
│   ├── cmd/                     # CLI commands (Cobra)
│   │   ├── root.go              # Root command
│   │   ├── deploy.go            # Deploy command
│   │   ├── status.go            # Status command
│   │   ├── list.go              # List deployments
│   │   └── init.go              # Init manifest command
│   ├── internal/                # Internal packages
│   │   ├── manifest/            # NVMS parsing and validation
│   │   │   ├── parser.go        # Manifest parser
│   │   │   ├── validator.go     # Schema validation
│   │   │   └── transformer.go   # Transform to deploy plan
│   │   ├── deploy/              # Deployment orchestration
│   │   │   ├── orchestrator.go  # Main deployment coordinator
│   │   │   ├── stages.go        # Deployment stages
│   │   │   └── rollback.go      # Rollback logic
│   │   ├── portfolio/           # Portfolio generation
│   │   │   ├── generator.go     # Template generator
│   │   │   ├── llm.go           # LLM backend interface
│   │   │   └── templates/       # Svelte component templates
│   │   ├── aws/                 # AWS client wrappers
│   │   │   ├── ec2.go           # EC2 operations
│   │   │   ├── ecs.go           # ECS operations
│   │   │   ├── lambda.go        # Lambda operations
│   │   │   └── apigateway.go    # API Gateway operations
│   │   ├── git/                 # Git operations
│   │   │   ├── clone.go         # Repository cloning
│   │   │   └── parser.go        # Repo URL parsing
│   │   └── config/              # Configuration management
│   │       ├── config.go        # App configuration
│   │       └── credentials.go   # AWS credential handling
│   ├── pkg/                     # Public packages
│   │   ├── nvms/                # NVMS types and interfaces
│   │   └── models/              # Shared data models
│   └── main.go                  # Entry point
├── bytebridge/                  # Bridge/integration layer
│   └── ByteBridge/              # External service integrations
└── nvms/                        # NVMS manifest parser (standalone)
    ├── main.go
    ├── Builder/                  # Build orchestration
    ├── Demonstrator/             # Portfolio generation
    ├── Provisioner/              # AWS provisioning
    └── projectManager/           # Project lifecycle management
```

### Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| CLI Framework | Cobra + Viper | Industry standard for Go CLIs, excellent flag/flag parsing |
| HTTP Framework | Gin | High performance, middleware ecosystem, mature |
| AWS SDK | aws-sdk-go-v2 | Official AWS SDK, modern Go idioms, context support |
| Database | SQLite (dev) / PostgreSQL (prod) | Zero-config dev, scalable production |
| LLM Client | Custom HTTP client | Lightweight, pluggable backend interface |
| Git Client | go-git | Pure Go Git implementation, no external dependencies |
| Logging | slog | Go 1.21+ standard library, structured logging |
| Testing | testify + httptest | Rich assertions, standard HTTP testing |

---

## Consequences

### Positive Consequences

1. **Modularity Enables Independent Testing**: Each service layer component can be tested in isolation with mocked dependencies. The manifest parser, deploy orchestrator, and portfolio generator have clear interfaces and can be unit tested independently.

2. **Go Provides Excellent AWS Integration**: The aws-sdk-go-v2 SDK offers first-class support for all AWS services BytePort targets. Context propagation, automatic retries, and credential chain handling are built-in.

3. **Single Binary Distribution**: Go compiles to static binaries, making CLI distribution trivial. No runtime dependencies, no virtual environments, no package managers required beyond the binary itself.

4. **Concurrent Deployment Support**: Go's goroutine model naturally supports concurrent deployment of multiple services defined in a single NVMS manifest. Each service can be provisioned in parallel with proper synchronization.

5. **Clear Separation of Concerns**: The layered architecture (entry points → services → infrastructure → data) makes the codebase navigable and maintainable. New team members can understand the flow quickly.

6. **Extensible LLM Backend Interface**: The `LLMBackend` interface allows swapping between OpenAI, LLaMA, or any future provider without changing the portfolio generation logic.

7. **SQLite for Zero-Config Development**: Developers can start contributing immediately without setting up a database server. SQLite handles the dev/test use case perfectly.

### Negative Consequences

1. **Go Error Handling Verbosity**: Go's explicit error handling (`if err != nil`) leads to verbose code, especially in the deployment orchestration layer where many AWS API calls are chained.

2. **No Generic ORM**: Go lacks a mature ORM like Django's or Rails'. Database interactions require either raw SQL, sqlc-generated code, or a lightweight ORM like GORM (which has its own complexity).

3. **Manual Dependency Injection**: Without a DI framework, wiring services together requires careful constructor patterns. This is manageable but requires discipline.

4. **AWS SDK Complexity**: The v2 SDK, while modern, has a steep learning curve. Each AWS service has its own client, input/output types, and error handling patterns.

5. **SQLite Limitations in Production**: While fine for development, SQLite doesn't support concurrent writes well. The production database must be PostgreSQL, requiring a migration strategy.

6. **Binary Size**: Go binaries include the entire runtime, resulting in 10-20MB binaries. This is acceptable for CLI tools but worth noting for container images.

7. **Cobra Command Complexity**: As the CLI grows, managing subcommands, flags, and help text in Cobra requires careful organization to avoid command sprawl.

---

## Architecture Diagrams

### Data Flow: Deploy Command

```
Developer                    CLI                        Backend Services              AWS
    │                         │                              │                        │
    │  byteport deploy        │                              │                        │
    │────────────────────────>│                              │                        │
    │                         │  1. Parse NVMS manifest      │                        │
    │                         │─────────────────────────────>│                        │
    │                         │                              │  Read manifest file    │
    │                         │                              │────────┐              │
    │                         │                              │        │              │
    │                         │                              │◀───────┘              │
    │                         │                              │                        │
    │                         │  2. Validate manifest        │                        │
    │                         │<─────────────────────────────│                        │
    │                         │  (schema, ports, services)   │                        │
    │                         │                              │                        │
    │                         │  3. Clone repository         │                        │
    │                         │─────────────────────────────>│                        │
    │                         │                              │  git clone             │
    │                         │                              │────────┐              │
    │                         │                              │        │              │
    │                         │                              │◀───────┘              │
    │                         │                              │                        │
    │                         │  4. Provision AWS resources  │                        │
    │                         │─────────────────────────────────────────────────────>│
    │                         │                              │  Create SG, ECS, etc. │
    │                         │                              │                        │
    │                         │                              │◀──────────────────────│
    │                         │                              │  Resources created     │
    │                         │                              │                        │
    │                         │  5. Deploy application       │                        │
    │                         │─────────────────────────────────────────────────────>│
    │                         │                              │  Push code, start svcs│
    │                         │                              │                        │
    │                         │                              │◀──────────────────────│
    │                         │                              │  Deploy complete       │
    │                         │                              │                        │
    │                         │  6. Generate portfolio       │                        │
    │                         │─────────────────────────────>│                        │
    │                         │                              │  LLM call             │
    │                         │                              │────────┐              │
    │                         │                              │        │              │
    │                         │                              │◀───────┘              │
    │                         │                              │                        │
    │  Deploy complete!       │  Result                     │                        │
    │<────────────────────────│<─────────────────────────────│                        │
    │  URL: https://...       │                              │                        │
    │                         │                              │                        │
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                    Component Interaction Map                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Cobra   │───►│ Manifest │───►│  Deploy  │───►│   AWS    │  │
│  │  CLI     │    │  Parser  │    │Orchestr. │    │  Client  │  │
│  └──────────┘    └──────────┘    └────┬─────┘    └──────────┘  │
│                                       │                         │
│                                       ▼                         │
│                                ┌──────────┐                     │
│                                │ Portfolio│                     │
│                                │Generator │                     │
│                                └────┬─────┘                     │
│                                     │                           │
│                                     ▼                           │
│                                ┌──────────┐                     │
│                                │   LLM    │                     │
│                                │ Backend  │                     │
│                                └──────────┘                     │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │   Gin    │───►│  Status  │───►│   AWS    │                  │
│  │  Server  │    │ Monitor  │    │  Client  │                  │
│  └──────────┘    └──────────┘    └──────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Code Examples

### Manifest Parser Interface

```go
// pkg/nvms/manifest.go
package nvms

import "fmt"

// Manifest represents a parsed NVMS manifest file
type Manifest struct {
    Name        string
    Description string
    Repo        string
    Branch      string
    Services    []Service
    Portfolio   Portfolio
}

// Service represents a single deployable service
type Service struct {
    Name  string
    Path  string
    Port  int
    Route string
    Env   map[string]string
    Type  string // "web", "api", "background", "worker"
}

// Portfolio represents portfolio generation settings
type Portfolio struct {
    Generate           bool
    LLM                string // "openai", "llama", "none"
    Template           string // "showcase", "minimal", "detailed"
    IncludeScreenshots bool
}

// Parse reads and validates an NVMS manifest file
func Parse(path string) (*Manifest, error) {
    // Implementation reads file, parses lines,
    // validates constraints, returns manifest
}

// Validate checks manifest constraints
func (m *Manifest) Validate() error {
    if m.Name == "" {
        return fmt.Errorf("manifest: NAME is required")
    }
    if m.Repo == "" {
        return fmt.Errorf("manifest: REPO is required")
    }
    if len(m.Services) == 0 {
        return fmt.Errorf("manifest: at least one SERVICE is required")
    }

    // Check for port conflicts
    ports := make(map[int]string)
    for _, svc := range m.Services {
        if svc.Port == 0 {
            return fmt.Errorf("manifest: service %q PORT is required", svc.Name)
        }
        if existing, ok := ports[svc.Port]; ok {
            return fmt.Errorf("manifest: port %d used by both %q and %q",
                svc.Port, existing, svc.Name)
        }
        ports[svc.Port] = svc.Name
    }

    return nil
}
```

### LLM Backend Interface

```go
// internal/portfolio/llm.go
package portfolio

import "context"

// LLMBackend defines the interface for LLM providers
type LLMBackend interface {
    // Generate produces text from a prompt
    Generate(ctx context.Context, prompt string) (string, error)

    // Name returns the provider name for logging
    Name() string
}

// OpenAIBackend implements LLMBackend using OpenAI API
type OpenAIBackend struct {
    APIKey     string
    Model      string
    HTTPClient HTTPClient
}

func (b *OpenAIBackend) Generate(ctx context.Context, prompt string) (string, error) {
    // Implementation calls OpenAI Chat Completions API
}

func (b *OpenAIBackend) Name() string {
    return "openai"
}

// LLaMABackend implements LLMBackend using local LLaMA
type LLaMABackend struct {
    Endpoint   string
    Model      string
    HTTPClient HTTPClient
}

func (b *LLaMABackend) Generate(ctx context.Context, prompt string) (string, error) {
    // Implementation calls local LLaMA HTTP server
}

func (b *LLaMABackend) Name() string {
    return "llama"
}

// FallbackBackend tries primary, falls back to secondary
type FallbackBackend struct {
    Primary   LLMBackend
    Secondary LLMBackend
}

func (fb *FallbackBackend) Generate(ctx context.Context, prompt string) (string, error) {
    result, err := fb.Primary.Generate(ctx, prompt)
    if err != nil && fb.Secondary != nil {
        return fb.Secondary.Generate(ctx, prompt)
    }
    return result, err
}

func (fb *FallbackBackend) Name() string {
    return fb.Primary.Name() + "+fallback"
}
```

### Deployment Orchestrator

```go
// internal/deploy/orchestrator.go
package deploy

import (
    "context"
    "fmt"
    "log/slog"
    "sync"

    "byteport/internal/aws"
    "byteport/internal/git"
    "byteport/internal/manifest"
    "byteport/internal/portfolio"
    "byteport/pkg/nvms"
)

// Orchestrator coordinates the full deployment pipeline
type Orchestrator struct {
    GitClient       *git.Client
    AWSClient       *aws.Client
    PortfolioGen    *portfolio.Generator
    ManifestParser  *manifest.Parser
    Logger          *slog.Logger
}

// Deploy executes the full deployment pipeline
func (o *Orchestrator) Deploy(ctx context.Context, manifestPath string) (*DeployResult, error) {
    // Stage 1: Parse and validate manifest
    m, err := o.ManifestParser.Parse(manifestPath)
    if err != nil {
        return nil, fmt.Errorf("manifest parse failed: %w", err)
    }

    o.Logger.Info("manifest parsed", "name", m.Name, "services", len(m.Services))

    // Stage 2: Clone repository
    repoPath, err := o.GitClient.Clone(ctx, m.Repo, m.Branch)
    if err != nil {
        return nil, fmt.Errorf("git clone failed: %w", err)
    }

    o.Logger.Info("repository cloned", "path", repoPath)

    // Stage 3: Provision and deploy services concurrently
    results := make(map[string]*ServiceResult)
    var mu sync.Mutex
    var wg sync.WaitGroup
    var deployErr error

    for _, svc := range m.Services {
        wg.Add(1)
        go func(svc nvms.Service) {
            defer wg.Done()

            result, err := o.deployService(ctx, svc, repoPath)
            mu.Lock()
            results[svc.Name] = result
            if err != nil {
                deployErr = err
            }
            mu.Unlock()
        }(svc)
    }

    wg.Wait()

    if deployErr != nil {
        o.Logger.Error("deployment failed", "error", deployErr)
        // Roll back any services that reached a provisioned state before returning.
        return nil, fmt.Errorf("deployment failed: %w", deployErr)
    }

    // Stage 4: Generate portfolio components
    var portfolioResult *portfolio.Result
    if m.Portfolio.Generate {
        portfolioResult, err = o.PortfolioGen.Generate(ctx, m, results)
        if err != nil {
            o.Logger.Warn("portfolio generation failed", "error", err)
            // Non-fatal: deployment succeeded even if portfolio gen failed
        }
    }

    return &DeployResult{
        Manifest:  m,
        Services:  results,
        Portfolio: portfolioResult,
    }, nil
}

func (o *Orchestrator) deployService(ctx context.Context, svc nvms.Service, repoPath string) (*ServiceResult, error) {
    o.Logger.Info("deploying service", "name", svc.Name, "port", svc.Port)

    // Create security group
    sgID, err := o.AWSClient.CreateSecurityGroup(ctx, svc.Name, svc.Port)
    if err != nil {
        return nil, fmt.Errorf("create security group: %w", err)
    }

    // Deploy based on service type
    var endpoint string
    switch svc.Type {
    case "web", "api":
        endpoint, err = o.AWSClient.DeployECS(ctx, svc, repoPath, sgID)
    case "background", "worker":
        endpoint, err = o.AWSClient.DeployLambda(ctx, svc, repoPath)
    default:
        return nil, fmt.Errorf("unsupported service type: %s", svc.Type)
    }

    if err != nil {
        return nil, fmt.Errorf("deploy %s: %w", svc.Name, err)
    }

    return &ServiceResult{
        Name:     svc.Name,
        Endpoint: endpoint,
        Status:   "running",
    }, nil
}
```

---

## Cross-References

- **ADR-002** (API Design Strategy): Defines the REST API exposed by the Gin HTTP server
- **ADR-003** (Frontend Framework Selection): Defines the SvelteKit web dashboard that consumes the backend API
- **Existing ADR-001** (NVMS Manifest Format): Defines the manifest format parsed by this architecture
- **Existing ADR-002** (AWS as Primary Target): Confirms AWS as the sole cloud provider for v1
- **Existing ADR-003** (Go Backend + Web Frontend): Confirms the technology choices formalized here
- **Existing ADR-004** (LLM-Assisted Generation): Defines the LLM integration pattern
- **Existing ADR-005** (CLI-First Interface): Confirms CLI as the primary interaction model
- **SOTA Research** (`docs/research/API_GATEWAYS_SOTA.md`): Provides technology landscape context

---

## Alternatives Considered

### Alternative 1: Rust Backend

**Pros**: Memory safety, zero-cost abstractions, excellent performance, growing ecosystem for AWS (aws-sdk-rust).

**Cons**: Steeper learning curve, longer compile times, smaller talent pool, more complex async model.

**Decision**: Rejected. Go's ecosystem maturity for CLI tools and AWS integration outweighs Rust's performance benefits for this use case. Rust may be reconsidered for the NanoVMS component.

### Alternative 2: Python Backend

**Pros**: Rich ecosystem, excellent AWS SDK (boto3), fast development cycle, strong LLM library support.

**Cons**: Slower execution, runtime dependencies, packaging complexity, GIL limits concurrency.

**Decision**: Rejected. CLI startup time and single-binary distribution requirements favor Go.

### Alternative 3: Node.js Backend

**Pros**: Large ecosystem, excellent for web services, same language as frontend.

**Cons**: Runtime dependencies, packaging complexity, less mature AWS SDK for CLI tools.

**Decision**: Rejected. Go's static compilation and CLI ergonomics are superior for this use case.

### Alternative 4: Microservices Architecture

**Pros**: Independent scaling, technology diversity per service, fault isolation.

**Cons**: Operational complexity, network latency, distributed tracing overhead, overkill for portfolio-scale deployments.

**Decision**: Rejected. BytePort's scope doesn't justify microservices complexity. A modular monolith provides sufficient separation of concerns.

---

## Implementation Notes

### Migration Path from Current Codebase

The current codebase has a flat structure in `backend/byteport/` and `backend/nvms/`. The migration to the new architecture should proceed in phases:

1. **Phase 1**: Extract NVMS parsing into `internal/manifest/` package
2. **Phase 2**: Create `internal/deploy/` orchestrator, move deployment logic
3. **Phase 3**: Extract AWS client wrappers into `internal/aws/`
4. **Phase 4**: Implement portfolio generation in `internal/portfolio/`
5. **Phase 5**: Add Cobra CLI structure in `cmd/`
6. **Phase 6**: Add Gin HTTP server for web dashboard API

### Testing Strategy

- **Unit Tests**: Each package tested in isolation with mocked dependencies
- **Integration Tests**: AWS operations tested against LocalStack
- **End-to-End Tests**: Full deploy pipeline tested against real AWS (CI/CD)
- **CLI Tests**: Cobra command testing with test factories

### Error Handling Convention

All errors must:
1. Be wrapped with context using `fmt.Errorf("context: %w", err)`
2. Be logged at the appropriate level (slog)
3. Be returned to the caller (no silent failures)
4. Include actionable information for the user (CLI) or operator (server)

---

*End of ADR-001*
