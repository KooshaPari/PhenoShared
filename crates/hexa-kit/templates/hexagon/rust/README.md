# Phenotype Kits Workspace

A curated collection of reusable Rust libraries for modern software development with hexagonal architecture.

## Packages

| Package | Description | Crates.io |
|---------|-------------|-----------|
| [clikit](clikit/) | Universal CLI framework | - |
| [agentkit](agentkit/) | Agent framework with skills | - |
| [evalkit](evalkit/) | Evaluation framework | - |
| [taskkit](taskkit/) | Task execution framework | - |
| [configkit](configkit/) | Configuration management | - |
| [authkit](authkit/) | Auth/AuthZ framework | - |
| [cachekit](cachekit/) | Caching abstraction | - |
| [logkit](logkit/) | Structured logging | - |
| [tracingkit](tracingkit/) | Distributed tracing | - |
| [metrickit](metrickit/) | Metrics collection | - |
| [eventkit](eventkit/) | Event-driven architecture | - |

## Architecture

All packages follow hexagonal (ports & adapters) architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    HEXAGONAL ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│  Domain Layer (Pure Business Logic)                          │
│  ├── Entities, Value Objects, Ports (interfaces)            │
│  └── Domain Services, Events                                │
├─────────────────────────────────────────────────────────────┤
│  Application Layer (Use Cases)                               │
│  ├── Commands, Queries, Services (CQRS)                    │
│  └── Application Services                                   │
├─────────────────────────────────────────────────────────────┤
│  Adapters Layer (Infrastructure)                            │
│  ├── Primary: CLI, HTTP, GraphQL                             │
│  └── Secondary: Database, Cache, Queue                      │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                        │
│  ├── Error Handling, Logging, Observability                 │
│  └── Cross-cutting Concerns                                 │
└─────────────────────────────────────────────────────────────┘
```

## xDD Methodologies (140+)

All packages apply these methodologies:

- **Development**: TDD, BDD, DDD, ATDD, SDD, FDD, CDD, IDD, MDD, RDD
- **Design**: DRY, KISS, YAGNI, SOLID (5), LoD, SoC, PoLA
- **Architecture**: Clean, Hexagonal, Onion, CQRS, Event Sourcing
- **Quality**: Property-Based, Mutation, Contract, Shift-Left, Chaos
- **Process**: DevOps, CI/CD, Agile, Scrum, Kanban, GitOps
- **Documentation**: ADR, RFC, Design Docs, Runbooks, SpecDD

## Getting Started

```bash
# Clone the workspace
git clone https://github.com/KooshaPari/kits.git
cd kits

# Build all packages
cargo build --workspace

# Run tests
cargo test --workspace

# Run benchmarks
cargo bench --workspace

# Check formatting
cargo fmt --all -- --check

# Run clippy
cargo clippy --workspace -- -D warnings
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow xDD methodologies
4. Add tests
5. Update documentation
6. Submit PR

## License

MIT OR Apache-2.0
