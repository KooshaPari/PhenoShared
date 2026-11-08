# AGENTS.md — hexagon

## Project Overview

- **Name**: hexagon (Hexagonal Architecture Framework)
- **Description**: Framework for implementing hexagonal architecture (ports and adapters) across multiple languages with consistent patterns
- **Location**: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/hexagon`
- **Language Stack**: Rust, Go, TypeScript, Python
- **Published**: Private (Phenotype org)

## Quick Start Commands

```bash
# Clone and setup
git clone https://github.com/KooshaPari/hexagon.git
cd hexagon

# Choose language implementation
cd rust && cargo build
cd go && go build ./...
cd ts && npm install && npm run build
cd py && pip install -e .

# Run tests
cargo test  # Rust
go test ./...  # Go
npm test  # TypeScript
pytest  # Python
```

## Architecture

### Hexagonal Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Input Adapters                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │   HTTP/REST     │  │   CLI           │  │   Message       │         │
│  │   Handler       │  │   Handler       │  │   Handler       │         │
│  │   (Controller)  │  │   (Command)     │  │   (Consumer)    │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
└───────────┼───────────────────┼───────────────────┼────────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                        Application Core                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Domain Logic                                  │   │
│  │                                                              │   │
│  │  ┌──────────────┐     ┌──────────────┐                    │   │
│  │  │    Ports     │────▶│   Services   │                    │   │
│  │  │  (Interfaces)│     │  (Use Cases) │                    │   │
│  │  └──────────────┘     └──────────────┘                    │   │
│  │         │                    │                            │   │
│  │         │            ┌───────┴───────┐                     │   │
│  │         │            ▼               ▼                     │   │
│  │         │      ┌──────────┐   ┌──────────┐                │   │
│  │         └─────▶│ Entities │   │ Value    │                │   │
│  │                │          │   │ Objects  │                │   │
│  │                └──────────┘   └──────────┘                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────┐
│                        Output Adapters                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Repository    │  │   External      │  │   Event         ││
│  │   (Database)    │  │   Service       │  │   Publisher     ││
│  │                 │  │   Client        │  │                 ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

### Dependency Rule

```
┌────────────────────────────────────────────────────────────────────┐
│                    Dependency Direction                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Adapters ──▶ Ports ──▶ Core Domain ──▶ Ports ──▶ Adapters        │
│                                                                     │
│  ┌─────────┐      ┌─────────┐      ┌─────────┐                     │
│  │  Input  │─────▶│         │      │         │                     │
│  │ Adapter │      │  Port   │─────▶│  Core   │                     │
│  └─────────┘      │Interface│      │ Domain  │                     │
│                   └─────────┘      └────┬────┘                     │
│                                         │                          │
│                   ┌─────────┐      ┌────┴────┐                     │
│  ┌─────────┐      │         │◀─────│         │                     │
│  │ Output  │◀─────│  Port   │      │         │                     │
│  │ Adapter │      │Interface│      └─────────┘                     │
│  └─────────┘      └─────────┘                                      │
│                                                                     │
│  Rule: Dependencies point INWARD to the domain core                  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## Quality Standards

### Multi-Language Quality

- **Rust**: rustfmt + clippy + nextest
- **Go**: gofmt + golangci-lint
- **TypeScript**: Prettier + ESLint
- **Python**: ruff + mypy

### Consistency Requirements

- Same patterns across languages
- Equivalent feature sets
- Compatible APIs where applicable
- Shared documentation

### Test Requirements

```bash
# Rust
cargo test
cargo nextest run

# Go
go test ./...

# TypeScript
npm test

# Python
pytest
```

## Git Workflow

### Branch Naming

Format: `<type>/<language>/<description>`

Types: `feat`, `fix`, `docs`, `refactor`, `port`

Examples:
- `feat/rust/add-async-ports`
- `fix/go/handle-nil-pointers`
- `port/ts/add-python-feature`
- `refactor/all/unify-error-types`

### Commit Messages

Format: `<type>(<scope>): <description>`

Examples:
- `feat(rust): implement async port interfaces`
- `fix(go): handle nil pointer edge cases in adapters`
- `port(ts): add Python feature parity for events`
- `refactor(all): unify error types across languages`

## File Structure

```
hexagon/
├── rust/                   # Rust implementation
│   ├── src/
│   ├── Cargo.toml
│   └── tests/
├── go/                     # Go implementation
│   ├── pkg/
│   ├── go.mod
│   └── *_test.go
├── ts/                     # TypeScript implementation
│   ├── src/
│   ├── package.json
│   └── tests/
├── py/                     # Python implementation
│   ├── hexagon/
│   ├── pyproject.toml
│   └── tests/
├── docs/                   # Shared documentation
│   ├── patterns/
│   └── examples/
└── examples/               # Cross-language examples
    ├── ecommerce/
    └── chat/
```

## CLI Commands

### Development

```bash
# Rust
cd rust && cargo build && cargo test

# Go
cd go && go build ./... && go test ./...

# TypeScript
cd ts && npm install && npm run build && npm test

# Python
cd py && pip install -e ".[dev]" && pytest
```

### Cross-Language Testing

```bash
# Run all tests
bun run test:all

# Run specific language
bun run test:rust
bun run test:go
bun run test:ts
bun run test:py
```

### Documentation

```bash
# Build docs
bun run docs:build

# Serve docs locally
bun run docs:serve

# Check links
bun run docs:check-links
```

## Troubleshooting

### Language-Specific Issues

```bash
# Rust - clean build
cd rust && cargo clean && cargo build

# Go - module issues
cd go && go mod tidy && go mod verify

# TypeScript - type errors
cd ts && rm -rf node_modules && npm install

# Python - environment
cd py && rm -rf .venv && python -m venv .venv
```

### Cross-Language Sync

```bash
# Check feature parity
bun run check:parity

# Update feature matrix
bun run update:matrix

# Sync examples
bun run sync:examples
```

## Environment Variables

```bash
# Development
HEXAGON_DEV_MODE=true
HEXAGON_LOG_LEVEL=debug

# Testing
HEXAGON_TEST_TIMEOUT=300
HEXAGON_COVERAGE_THRESHOLD=80

# Language-specific
CARGO_TERM_COLOR=always
GO111MODULE=on
```

## Language Feature Matrix

| Feature | Rust | Go | TypeScript | Python |
|---------|------|-----|------------|---------|
| Ports | ✅ | ✅ | ✅ | ✅ |
| Adapters | ✅ | ✅ | ✅ | ✅ |
| Events | ✅ | ✅ | ✅ | ✅ |
| Async | ✅ | ✅ | ✅ | ✅ |
| DI Container | ✅ | ✅ | ✅ | ✅ |

## Integration Points

| System | Protocol | Purpose |
|--------|----------|---------|
| PhenoMCP | All | Multi-language SDK |
| HeliosApp | All | Framework adoption |
| TheGent | All | Tool integration |

---

Last Updated: 2026-04-05
Version: 1.0.0
