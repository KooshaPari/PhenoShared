# Claude AI Agent Guide — template-lang-kotlin

This repository is designed to work seamlessly with Claude (and other advanced AI agents) as an autonomous software engineer.

## Quick Start

```bash
# Initialize a new Kotlin project
./gradlew init

# Run tests
./gradlew test

# Build
./gradlew build

# Clean
./gradlew clean
```

## Repository Mental Model

### Project Structure

```
src/
  main/kotlin/<package>/
    domain/           # Business logic, entities, value objects
      model/          # Domain models
      service/        # Domain services
      repository/     # Repository interfaces (ports)
    application/      # Use cases, application services
      usecase/        # Application use cases
      dto/            # Data transfer objects
    adapters/         # External integrations
      api/            # REST/GraphQL adapters
      persistence/    # Database adapters
      external/       # External service clients
    infrastructure/   # Framework, DI, configuration
      di/             # Koin modules
      config/         # Configuration classes
```

### Build Configuration

- **Build Tool:** Gradle with Kotlin DSL
- **Kotlin Version:** 1.9.0+
- **JVM Target:** 17 (minimum), 21 (recommended)
- **DI Framework:** Koin 3.5+
- **Serialization:** Kotlinx Serialization

### Style Constraints

- **Line length:** 120 characters
- **Formatter:** ktlint
- **Linter:** ktlint with custom rules
- **File size:** ≤500 lines (target ≤350)
- **Package naming:** `com.phenotype.<module>`

### Agent Must

- Use Kotlin idioms (extension functions, DSLs, coroutines)
- Prefer immutability (data classes, vals)
- Use Coroutines for async, never blocking
- Document public APIs with KDoc
- Use sealed classes for error types
- Test domain logic in isolation

## Standard Operating Loop

1. **Review** - Read specs, understand requirements
2. **Research** - Check existing patterns in codebase
3. **Plan** - Formulate implementation approach
4. **Execute** - Implement in small steps
5. **Test** - Verify with unit tests
6. **Polish** - Lint, format, review

## CLI Reference

```bash
# Build
./gradlew build

# Test
./gradlew test
./gradlew test --tests "*TestClass"

# Lint
./gradlew lint
./gradlew ktlintCheck

# Format
./gradlew ktlintFormat

# Dependencies
./gradlew dependencies
./gradlew dependencyUpdates

# Clean
./gradlew clean
./gradlew clean build --refresh-dependencies
```

## Architecture Patterns

### Hexagonal Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Adapters                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   REST API  │  │  Database   │  │  External   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
└─────────┼────────────────┼────────────────┼────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────┐
│                 Application Layer                   │
│              Use Cases, DTOs, Services              │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│                   Domain Layer                      │
│         Entities, Value Objects, Services          │
│  ┌─────────────────────────────────────────────┐   │
│  │              Repository Ports                │   │
│  │  (Interfaces defined in domain, impl in     │   │
│  │   adapters)                                  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Error Handling

```kotlin
// Sealed class for domain errors
sealed class DomainError {
    data class NotFound(val id: String) : DomainError()
    data class Validation(val message: String) : DomainError()
    data class Unauthorized(val userId: String) : DomainError()
}

// Result wrapper for operations
suspend fun <T> runCatching(block: suspend () -> T): Result<T> = try {
    Result.success(block())
} catch (e: Exception) {
    Result.failure(e)
}

// Usage in use case
suspend fun getUser(id: UserId): User = runCatching {
    repository.findById(id) ?: throw DomainError.NotFound(id.toString())
}.getOrThrow()
```

## Testing Patterns

```kotlin
// Domain test - pure functions
class UserServiceTest {
    @Test
    fun `should create user with hashed password`() {
        // Given
        val rawPassword = "secure123"

        // When
        val user = User.create(email, rawPassword)

        // Then
        assertTrue(user.passwordHash.startsWith("$2a$"))
        assertTrue(user.passwordHash.length == 60)
    }
}

// Integration test with testcontainer
class UserRepositoryTest {
    @Container
    val postgres = PostgreSQLContainer<Nothing>("postgres:15")

    @Test
    fun `should persist and retrieve user`() = runTest {
        val repo = PostgresUserRepository(testDb)
        val user = User.create(email, password)

        repo.save(user)
        val found = repo.findById(user.id)

        assertEquals(user.email, found?.email)
    }
}
```

## Security Guidelines

- Never hardcode secrets; use environment variables
- Validate all input with domain rules, not just type checks
- Use parameterized queries for database operations
- Hash passwords with BCrypt (Argon2 for new projects)
- Rate limit API endpoints
- Log security events (auth failures, access denied)

## Common Workflows

### Adding a New Use Case

1. Create use case class in `application/usecase/`
2. Define input/output DTOs
3. Implement business logic in domain layer
4. Write unit tests
5. Wire up in DI module

### Adding a New Adapter

1. Create adapter class in `adapters/<type>/`
2. Implement corresponding port interface
3. Configure in DI module
4. Write integration test

## Troubleshooting

```bash
# Dependency conflicts
./gradlew build --refresh-dependencies

# Slow builds
./gradlew --stop
rm -rf ~/.gradle/caches

# Test failures
./gradlew test --info | grep -A 10 "FAILED"

# IDE issues
./gradlew idea
./gradlew eclipse
```
