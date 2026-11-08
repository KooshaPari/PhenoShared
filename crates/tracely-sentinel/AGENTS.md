# AGENTS.md — phenotype-sentinel

## Project Identity

- **Name**: phenotype-sentinel
- **Description**: Rust resilience library with rate limiting, circuit breaking, and bulkhead isolation
- **Location**: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/phenotype-sentinel`
- **Language Stack**: Rust (edition 2021)
- **Type**: Library/Infrastructure

## Agent Responsibilities

### Forge (Implementation)
- Implement resilience primitives per specifications
- Add new policies (thresholds, window sizes)
- Ensure async-safety across all primitives
- Write unit tests with FR traceability

### Helios (Testing)
- Run `cargo test` before any PR
- Verify concurrent access safety
- Performance test under load
- Bench high-frequency rate limiting

## Development Commands

```bash
cargo check    # Type check
cargo test     # Run tests
cargo clippy   # Lint
cargo fmt      # Format code
```

## Quality Standards

- **Clippy warnings**: Zero tolerance (`-D warnings`)
- **Thread-safety**: All primitives must be `Send + Sync`
- **Async-safe**: No blocking operations in async contexts
- **FR traceability**: All tests MUST reference FR identifiers

## Branch Discipline

- Feature branches: `feat/<feature-name>`
- Bug fixes: `fix/<issue-name>`
- Worktrees preferred for parallel work

## CI/CD

- GitHub Actions workflow in `.github/workflows/`
- Must pass before merge to main
