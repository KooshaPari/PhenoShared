# AGENTS.md — phenotype-vessel

## Project Identity

- **Name**: phenotype-vessel
- **Description**: Rust container utilities library (Docker, Podman, containerd)
- **Location**: `/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-vessel`
- **Language Stack**: Rust (edition 2021)
- **Type**: Library/Infrastructure

## Agent Responsibilities

### Forge (Implementation)
- Implement container runtime abstractions
- Add support for new container runtimes
- Maintain async-first design (tokio)
- Write unit tests with FR traceability

### Helios (Testing)
- Run `cargo test` before any PR
- Verify container operations (requires Docker/Podman)
- Test error handling for runtime failures
- Integration test multi-container scenarios

## Development Commands

```bash
cargo check    # Type check
cargo test     # Run tests
cargo clippy   # Lint
cargo fmt      # Format code
```

## Quality Standards

- **Clippy warnings**: Zero tolerance (`-D warnings`)
- **Trait-based**: Abstract over runtimes via traits
- **Typed errors**: No silent failures
- **FR traceability**: All tests MUST reference FR identifiers

## Branch Discipline

- Feature branches: `feat/<feature-name>`
- Bug fixes: `fix/<issue-name>`
- Worktrees preferred for parallel work

## CI/CD

- GitHub Actions workflow in `.github/workflows/`
- Must pass before merge to main
