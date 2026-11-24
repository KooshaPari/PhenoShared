# Pheno-Utils

Unified CLI utilities for the Phenotype ecosystem.

## Overview

`pheno-utils` is a unified command-line interface that consolidates various development utilities from the phenoSDK tools. It provides a single, consistent interface for common development tasks like dependency analysis, health checks, file size validation, and more.

## Installation

```bash
# Install from source
pip install /path/to/PhenoKit/python/pheno-utils

# Or with development dependencies
pip install /path/to/PhenoKit/python/pheno-utils[dev]
```

## Usage

### Dependency Analysis

```bash
# Analyze dependencies in a project
pheno-utils deps /path/to/project

# Generate Mermaid diagram
pheno-utils deps /path/to/project --format mermaid --output deps.mmd

# Generate from existing analysis
pheno-utils mermaid dependency_analysis.json --output graph.mmd
```

### Health Checks

```bash
# Run all health checks
pheno-utils health /path/to/project

# Run specific checks
pheno-utils health /path/to/project --check imports
pheno-utils health /path/to/project --check structure
pheno-utils health /path/to/project --check config

# Output as JSON
pheno-utils health /path/to/project --json
```

### File Size Validation

```bash
# Check file sizes (default limits: 500 hard, 350 target)
pheno-utils sizes /path/to/project

# Custom limits
pheno-utils sizes /path/to/project --limit 400 --target 300

# Strict mode (fail on warnings)
pheno-utils sizes /path/to/project --strict

# Generate report only (no fail)
pheno-utils sizes /path/to/project --report
```

### Lines of Code Counter

```bash
# Count logical LOC
pheno-utils loc /path/to/project

# Custom threshold
pheno-utils loc /path/to/project --threshold 10000

# Exclude patterns
pheno-utils loc /path/to/project --exclude tests --exclude docs

# Output as JSON
pheno-utils loc /path/to/project --json
```

### Public API Inventory

```bash
# Generate JSON inventory
pheno-utils inventory /path/to/project

# Generate Markdown
pheno-utils inventory /path/to/project --format md --output API.md
```

### Import Migration

```bash
# Dry-run migration
pheno-utils migrate /path/to/project

# Apply migration
pheno-utils migrate /path/to/project --apply

# Version-specific migration
pheno-utils migrate /path/to/project --from 1.x --to 2.0 --apply
```

### Docstring Simplification

```bash
# Preview changes (dry-run)
pheno-utils simplify-docs /path/to/project/src

# Apply changes
pheno-utils simplify-docs /path/to/project/src --no-dry-run
```

### Repository Validation

```bash
# Validate repository hygiene
pheno-utils validate /path/to/project

# Strict mode (fail on any issues)
pheno-utils validate /path/to/project --strict

# Custom large file threshold
pheno-utils validate /path/to/project --threshold 2000000
```

### Code Map Generation

```bash
# Generate code map
pheno-utils codemap /path/to/project

# Output as formatted text
pheno-utils codemap /path/to/project --no-json

# Save to file
pheno-utils codemap /path/to/project --output codemap.json
```

## Command Reference

| Command | Description |
|---------|-------------|
| `deps` | Analyze project dependencies |
| `mermaid` | Generate Mermaid dependency diagrams |
| `health` | Run project health checks |
| `sizes` | Validate file sizes |
| `loc` | Count lines of code |
| `inventory` | Generate public API inventory |
| `migrate` | Migrate import statements |
| `simplify-docs` | Simplify verbose docstrings |
| `validate` | Validate repository hygiene |
| `codemap` | Generate code map of pheno references |
| `version` | Show version information |

## Module Structure

```
pheno_utils/
├── __init__.py          # Package initialization
├── cli.py               # Unified Typer CLI
├── dependencies.py      # Dependency analysis
├── file_sizes.py        # File size checking
├── loc_counter.py       # LOC counting
├── inventory.py         # API inventory
├── migration.py         # Import migration
├── docstrings.py        # Docstring simplification
├── cleanup.py           # Repository validation
├── codemap.py           # Code map generation
└── health.py            # Health checks
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linting
ruff check src/
ruff format src/

# Run type checking
mypy src/pheno_utils

# Run tests
pytest
```

## Migration from phenoSDK Tools

The following phenoSDK tools have been consolidated into `pheno-utils`:

| Old Tool | New Command |
|----------|-------------|
| `analyze_dependencies.py` | `pheno-utils deps` |
| `atlas_health_cli.py` | `pheno-utils health` |
| `check_file_sizes.py` | `pheno-utils sizes` |
| `count_loc.py` | `pheno-utils loc` |
| `inventory_public_api.py` | `pheno-utils inventory` |
| `migrate_imports.py` | `pheno-utils migrate` |
| `simplify_docstrings.py` | `pheno-utils simplify-docs` |
| `validate_cleanup.py` | `pheno-utils validate` |
| `generate_phen_codemap.py` | `pheno-utils codemap` |
| `render_dependency_mermaid.py` | `pheno-utils mermaid` |

## License

MIT License - See LICENSE file for details.
