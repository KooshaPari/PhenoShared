# Plugin Architecture TypeScript Template

A production-ready plugin architecture template for TypeScript/Node.js projects.

## Architecture

```
plugin-typescript/
├── src/
│   ├── domain/                    # Core business logic (no external deps)
│   │   ├── entities/            # Domain models
│   │   ├── value-objects/      # Immutable value types
│   │   ├── ports/              # Interface definitions
│   │   ├── services/            # Domain services
│   │   └── errors/              # Domain errors
│   │
│   ├── application/              # Application layer
│   │   ├── commands/           # Write operations (CQRS)
│   │   ├── queries/             # Read operations (CQRS)
│   │   └── dtos/               # Data transfer objects
│   │
│   ├── infrastructure/            # Infrastructure layer
│   │   ├── adapters/            # Database, cache adapters
│   │   ├── logging/            # Logging
│   │   └── validation/          # Validation adapters (Zod)
│   │
│   └── interfaces/               # Interface adapters
│       ├── api/                 # HTTP handlers
│       ├── cli/                 # CLI commands
│       └── plugins/             # Plugin system
│
└── tests/
    ├── unit/                   # Unit tests
    └── integration/            # Integration tests
```

## Key Principles Applied

- **Interface Segregation**: Small, focused interfaces (ISP)
- **Dependency Inversion**: Domain depends on abstractions
- **Plugin Architecture**: Extensible via plugin system
- **CQRS**: Command Query Responsibility Segregation
- **Discriminated Unions**: Type-safe error handling
- **Strict TypeScript**: Strict mode for type safety

## Wrap-Over Pattern Applied

| Pattern | Library | Why |
|---------|---------|-----|
| Validation | Zod | Runtime type safety, schema inference |
| Logging | Pino | Structured, async-compatible |
| Serialization | Native JSON | Built-in, fast enough |

## Plugin System

```typescript
import { Plugin, PluginRegistry } from './domain/ports';

// Define a plugin
class MyPlugin implements Plugin {
  readonly name = 'my-plugin';
  readonly version = '1.0.0';

  async initialize() {
    // Setup plugin resources
  }

  async shutdown() {
    // Cleanup plugin resources
  }
}

// Register and use
const registry: PluginRegistry = new PluginRegistryImpl();
await registry.register(new MyPlugin());
```

## Getting Started

```bash
# Generate a new project
cp -r plugin-typescript new-project
cd new-project

# Update package.json with your project name

# Install dependencies
npm install

# Build
npm run build

# Run tests
npm test

# Run linter
npm run lint
```

## Testing Strategy

- **Unit Tests**: Domain layer with Vitest
- **Integration Tests**: Test adapters with mocks
- **Plugin Tests**: Test plugin loading/unloading

## See Also

- [xDD Methodologies Reference](../reference/xDD/XDD_METHODOLOGIES.md)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Plugin Architecture Pattern](https://martinfowler.com/articles/patterns-of-enterprise-application-architecture/Plugin.html)
