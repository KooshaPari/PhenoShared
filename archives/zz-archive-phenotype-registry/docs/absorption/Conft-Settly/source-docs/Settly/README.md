# settly

**Universal configuration management with layered configs, validation, and environment support.**

A hexagonal architecture-based configuration framework supporting:

- **Layered Configuration**: Merge, override, and prioritize configs from multiple sources
- **Validation**: Schema-based validation with custom validators
- **Environment Support**: Development, staging, production with overrides
- **Multiple Formats**: TOML, YAML, JSON, ENV, CLI arguments
- **Hot Reload**: Watch and reload configuration files
- **Type Safety**: Strongly-typed configuration with serde

## Architecture

```
settly/
├── src/
│   ├── domain/          # Core domain logic (pure)
│   │   ├── config/     # Configuration entities and value objects
│   │   ├── layers/     # Configuration layer management
│   │   ├── sources/    # Configuration source definitions
│   │   ├── validation/ # Validation rules and schemas
│   │   ├── ports/      # Interface definitions
│   │   └── errors/     # Domain errors
│   ├── application/    # Application services
│   │   ├── builder/   # Configuration builder
│   │   └── loader/    # Configuration loader
│   ├── adapters/      # Infrastructure adapters
│   │   ├── sources/   # File, env, CLI sources
│   │   ├── formats/   # TOML, YAML, JSON parsers
│   │   └── validators/ # Built-in validators
│   └── infrastructure/ # Cross-cutting concerns
├── tests/             # Integration tests
├── examples/          # Usage examples
└── benches/           # Benchmarks
```

## Features

- [x] Layered configuration with merge strategies
- [x] Multiple file format support (TOML, YAML, JSON)
- [x] Environment variable interpolation
- [x] CLI argument overrides
- [x] Schema-based validation
- [x] Hot reload support
- [x] Type-safe configuration access
- [ ] Secret management integration
- [ ] Remote configuration support
- [ ] Configuration versioning

## Installation

```toml
[dependencies]
settly = "0.1"
```

## Quick Start

```rust
use settly::{Config, ConfigBuilder};

let config = ConfigBuilder::new()
    .with_file("config.toml")?
    .with_env()
    .with_cli_args()
    .build()?;

let value: String = config.get("database.url")?;
```

## Documentation

- [API Documentation](https://docs.rs/settly)
- [User Guide](https://settly.dev/guide)
- [xDD Methodologies](STANDARDS.md)

## License

MIT OR Apache-2.0
