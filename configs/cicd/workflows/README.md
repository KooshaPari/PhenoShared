# E2E Workflows

Production-ready end-to-end workflows for repository management, auditing, and scaffolding.

## Workflows

| Workflow | Purpose |
|----------|---------|
| `e2e-branch-pr-workflow.sh` | Scan repos, manage PRs, clean up branches |
| `e2e-repo-cleanup-workflow.sh` | Clean merged branches, stale worktrees, optimize repos |
| `e2e-xdd-audit-workflow.sh` | Audit repos for xDD architecture compliance |
| `e2e-scaffold-workflow.sh` | Generate new microservices from templates |

## Quick Start

```bash
cd /Users/<REDACTED>/CodeProjects/Phenotype/repos/template-commons/workflows

# Dry run (preview actions)
./e2e-branch-pr-workflow.sh --dry-run

# Scan specific repo
./e2e-xdd-audit-workflow.sh --repo AgilePlus

# Scaffold new microservice
./e2e-scaffold-workflow.sh --name my-service --lang go
```

## e2e-branch-pr-workflow.sh

Scan all phenotype repos and manage branches/PRs.

```bash
# Scan all phenotype repos
./e2e-branch-pr-workflow.sh

# Scan specific repo
./e2e-branch-pr-workflow.sh --repo phench

# Dry run (no changes)
./e2e-branch-pr-workflow.sh --dry-run
```

**Features:**
- Scan worktrees for unpushed commits
- List open PRs
- Create PRs for branches
- Merge/close PRs
- Clean up stale worktrees

## e2e-repo-cleanup-workflow.sh

Clean up merged branches and optimize repositories.

```bash
# Clean all phenotype repos (dry run)
./e2e-repo-cleanup-workflow.sh --dry-run

# Clean specific repo
./e2e-repo-cleanup-workflow.sh --repo AgilePlus

# Apply changes (non-dry-run)
./e2e-repo-cleanup-workflow.sh
```

**Features:**
- Delete merged local branches
- Delete merged remote branches
- List/manage worktrees
- Prune git reflog
- Clean untracked files
- Sync with remote

## e2e-xdd-audit-workflow.sh

Audit repositories for xDD architecture compliance.

```bash
# Audit all phenotype repos
./e2e-xdd-audit-workflow.sh

# Audit specific repo
./e2e-xdd-audit-workflow.sh --repo phenotype-go-kit

# Output to file
./e2e-xdd-audit-workflow.sh --output audit-report.md
```

**Checks:**
- Hexagonal architecture indicators
- SOLID principles compliance
- Testing practices (TDD, BDD)
- Documentation (README, ADR, API docs)
- CI/CD configuration
- Observability (logging, metrics, tracing)

**Scoring:**
| Score | Status |
|-------|--------|
| 80-100% | Excellent |
| 60-79% | Good, improvements possible |
| <60% | Needs refactoring |

## e2e-scaffold-workflow.sh

Generate new microservices from templates.

```bash
# Scaffold Go microservice
./e2e-scaffold-workflow.sh --name my-service --lang go

# Scaffold Python microservice
./e2e-scaffold-workflow.sh --name my-service --lang python

# Scaffold to specific directory
./e2e-scaffold-workflow.sh --name my-service --lang rust --output /path/to/output
```

**Supported Languages:**
| Language | Template | Description |
|----------|----------|-------------|
| `go` | hexagonal-go | Go hexagonal with CQRS |
| `python` | microservice-scaffold/python | FastAPI + hexagonal |
| `rust` | clean-rust | Rust clean architecture |
| `typescript` | plugin-typescript | TypeScript plugin system |

**Features:**
- Copies template to new location
- Updates module/package names
- Initializes git repo
- Generates README with xDD patterns

## xDD Patterns Applied

All templates include:

- **Hexagonal Architecture**: Domain isolated from infrastructure
- **CQRS**: Commands and queries separation
- **Ports & Adapters**: Dependency inversion via interfaces
- **Event-Driven**: NATS/Kafka adapters
- **Observability**: Structured logging, Prometheus, OpenTelemetry
- **SOLID**: All principles applied
- **DRY/KISS/YAGNI**: Throughout

## Dependencies

- `gh` - GitHub CLI
- `git` - Git version control
- `jq` - JSON processor
- `fd` - Fast file finder (optional, for audit)
- `ripgrep` - Fast regex search (optional, for audit)

## Configuration

Edit these variables at the top of each script:

```bash
# Base path for repositories
BASE_PATH="/Users/<REDACTED>/CodeProjects/Phenotype/repos"

# Phenotype repos to scan
PHENOTYPE_REPOS=(
    "AgilePlus"
    "agileplus-publish"
    "phenotype-design"
    "phenotype-go-kit"
    "phenotype-skills-clone"
    "phench"
    "phenodocs"
)
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid args, missing deps) |

## See Also

- [xDD Methodologies Reference](../docs/reference/xDD/XDD_METHODOLOGIES.md)
- [Library Decomposition Guide](../docs/guides/LIBRARY_DECOMPOSITION.md)
- [Template Templates](../README.md)
