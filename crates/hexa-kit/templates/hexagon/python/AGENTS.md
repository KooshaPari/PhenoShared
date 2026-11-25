# AGENTS.md - HexaPy

## Project Overview

- **Name**: HexaPy
- **Description**: Hexagonal Architecture Kit for Python
- **Language**: Python (3.10+)
- **Location**: Phenotype repos shelf

## Features

- **Hexagonal Architecture**: Ports & Adapters pattern
- **Zero dependencies in domain**: Pure business logic
- **Event sourcing support**: Built-in domain events
- **Async support**: Full async/await compatibility

## Architecture

```
┌─────────────────────────────────────────┐
│              Adapters Layer              │
├─────────────────────────────────────────┤
│                Ports Layer               │
├─────────────────────────────────────────┤
│               Domain Layer               │
│        (ZERO external dependencies)      │
├─────────────────────────────────────────┤
│             Application Layer             │
└─────────────────────────────────────────┘
```

## Agent Rules

### Project-Specific Rules

1. **Domain Layer Purity**
   - Zero external dependencies in domain
   - Pure Python, no framework imports
   - Immutable value objects
   - Rich domain models

2. **Port Interfaces**
   - Define ports as abstract base classes
   - InputPort for driving adapters
   - OutputPort for driven adapters
   - Repository, EventStore, MessageBus patterns

3. **Python Idioms**
   - Use type hints throughout
   - Follow PEP 8 with Black formatting
   - Dataclasses for DTOs
   - Protocol classes for structural typing

### Phenotype Org Standard Rules

1. **UTF-8 encoding** in all text files
2. **Worktree discipline**: canonical repo stays on `main`
3. **CI completeness**: fix all CI failures before merging
4. **Never commit** agent directories (`.claude/`, `.codex/`, `.cursor/`)

## Quality Standards

```bash
# Install
pip install -e ".[dev]"

# Test
pytest

# Coverage
pytest --cov=pyhex

# Type check
mypy pyhex

# Format
black --check pyhex
ruff check pyhex
```

## Git Workflow

1. Create feature branch: `git checkout -b feat/my-feature`
2. Add tests for new functionality
3. Ensure type checking passes
4. Format with Black
5. Create PR with examples
