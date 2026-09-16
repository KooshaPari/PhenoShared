# pheno-harness Migration Guide

## Version Migration

### v0.1.x to v0.2.x
- Adapter interface changes
- Config format: YAML

### Data Migration
- Benchmark results: JSON
- Eval traces: JSONL
- No database required

### CI/CD Migration
- Test runner: pytest
- Lint: ruff + mypy
- Format: prettier
