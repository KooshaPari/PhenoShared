# Contributing to HexaType

First off, thank you for considering contributing to **HexaType**! It's people like you who make this hexagonal architecture template better for everyone.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct.

## How Can I Contribute?

### Reporting Bugs

- Use the Bug Report issue template
- Provide a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Include Node.js version and package manager (pnpm/npm/yarn)

### Suggesting Enhancements

- Check the Issues to see if the enhancement has already been suggested
- Use the Feature Request issue template
- Describe the use case and why it would benefit the project

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes (`pnpm test`)
5. Make sure your code lints (`pnpm lint`)
6. Format your code (`pnpm format`)

#### Branch Naming

```
feat/<feature-name>     # New features
fix/<bug-description>  # Bug fixes
docs/<topic>           # Documentation
refactor/<area>        # Code refactoring
```

#### Commit Messages

Follow conventional commits:

```
feat(domain): add entity base class
fix(ports): correct interface definition
docs(readme): update quick start example
```

## Development Setup

```bash
# Install dependencies
pnpm install

# Run tests
pnpm test

# Run linter
pnpm lint

# Type check
pnpm typecheck

# Format code
pnpm format
```

## Architecture Guidelines

HexaType follows hexagonal architecture principles:

- **Domain Layer**: Pure business logic, no side effects
- **Ports Layer**: Interface definitions (driving/driven)
- **Application Layer**: Use cases and orchestration
- **Adapters Layer**: External integrations (REST, gRPC, CLI)

### Key Principles

1. **Dependency Rule**: Dependencies point toward domain
2. **Pure Domain**: Domain has no external dependencies
3. **Interface Segregation**: Small, focused port interfaces
4. **TypeScript Best Practices**: Strict mode, proper typing

## Code Style

- Use ESLint and Prettier configuration provided
- Follow TypeScript best practices
- Write JSDoc comments for exported functions
- Use meaningful variable and function names
- Leverage type system for validation

## License

By contributing, you agree that your contributions will be licensed under the MIT license.

---

Thank you for your contributions!
