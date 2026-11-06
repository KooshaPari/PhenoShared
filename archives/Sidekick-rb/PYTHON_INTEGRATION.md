# Python Integration — Sidekick

## Polyglot Workspace Structure

Sidekick mixes Rust (compiled) and Python (runtime) utilities:

### Rust Crates

- **sidekick-dispatch**: CLI dispatcher (compiled binary + library)
- Managed by root `Cargo.toml` workspace

### Python Packages

- **sidekick-presence**: Agent presence tracking (Python + launchd)
- **sidekick-cheap-llm**: FastMCP budget LLM routing (Python)

## Python Setup

Each Python package has its own `pyproject.toml`. For workspace-level integration:

```bash
cd crates/sidekick-presence && pip install -e .
cd crates/sidekick-cheap-llm && pip install -e .
```

Or, create a root `pyproject.toml` with dependencies on both sub-packages (future enhancement).

## Testing

```bash
# Rust crates
cd /path/to/Sidekick
cargo test --workspace

# Python packages
cd crates/sidekick-presence && python -m pytest
cd crates/sidekick-cheap-llm && python -m pytest
```

## Publishing

- **Rust**: `cargo publish --package sidekick-dispatch`
- **Python**: `python -m build` + `twine upload` for each package

## Future: Unified Workspace

When Python sub-packages mature, consolidate via:
- Root `pyproject.toml` declaring them as local editable dependencies
- Pixi integration for unified environment management
