# Development Standards

## xDD Methodologies Applied

### Development
- **TDD**: Write failing tests before implementation
- **BDD**: Define behavior with Gherkin
- **DDD**: Map to domain concepts
- **ATDD**: Define acceptance criteria first

### Design Principles
- **SOLID**: Single responsibility, Open/closed, Liskov, Interface segregation, Dependency inversion
- **DRY**: Don't repeat yourself
- **KISS**: Keep it simple

### Architecture
- **Clean Architecture**: Dependencies point inward
- **Hexagonal**: Ports and adapters isolation

## Code Quality Gates

| Gate | Tool |
|------|------|
| Linting | golangci-lint |
| Formatting | go fmt |
| Testing | go test |

## Commit Convention

```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
```

## PR Requirements

- [ ] Tests pass
- [ ] Lint passes
- [ ] go fmt applied
- [ ] Documentation updated
