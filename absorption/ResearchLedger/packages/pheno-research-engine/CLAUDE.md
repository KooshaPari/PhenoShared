# phenotype-research-engine

Phenotype research and investigation engine. Orchestrates automated research workflows, evidence gathering, and analysis for agent-driven investigation pipelines.

## Stack
- Language: Python (primary), TypeScript (secondary)
- Key deps: pytest, pyproject.toml, tsconfig.json
- Status: Archived (see ARCHIVED.md)

## Structure
- `src/`: Python source for research orchestration
- `tests/`: pytest test suite

## Key Patterns
- Evidence-driven: all research outputs include source provenance
- Composable research steps as DAG tasks
- Integrates with phenotype-task-engine for scheduling

## Adding New Functionality
- New research modules: add in `src/`
- Tests required before implementation (TDD)
- Run `pytest` to verify
