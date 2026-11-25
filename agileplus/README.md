# repos — CodeProjects/Phenotype organizational shelf

This is the **repos shelf**: a polyrepo containing ~30 independent projects
organized under `CodeProjects/Phenotype/organizational-shelf/repos`.

## What is a shelf?

A shelf is an organizational layer above individual projects. Think of it like
`~/code/` or `/opt/` — a directory containing related but independent repositories.
Each project is a standalone git repo; the shelf is their shared home.

## Quick Start

### Finding a project
```bash
find . -maxdepth 1 -mindepth 1 -type d | sort
cat README.md          # Read the target project README first
```

### Working on a project
```bash
cd <project-name>      # e.g., cd heliosCLI
git status             # Verify you're in the right place
```

### Creating a worktree
```bash
git worktree add .worktrees/my-feature -b my-feature
cd .worktrees/my-feature
```

## Project Categories

Projects are organized into functional categories at the top level:

| Category | Contents |
|----------|----------|
| `apps/` | User-facing applications |
| `tooling/` | Developer tools, CLIs, scripts |
| `infra/` | Infrastructure, deployment, devops |
| `libs/` | Shared libraries and packages |
| `platforms/` | Platform-as-product projects |

Note: Not all projects are yet in these categories — the reorganization is ongoing.
Use the target project's `README.md` and `CLAUDE.md` for the authoritative list.

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Shelf overview and project pointers |
| `AGENTS.md` | Agent interaction rules |
| `GOVERNANCE.md` | Shelf governance |
| `CLAUDE.md` | Claude Code settings |

## Architecture

```
repos/                          # ← Shelf root (YOU ARE HERE)
├── .worktrees/                 # Worktree staging area
├── .archive/                    # Archived projects
├── .claude/                     # Shelf-level Claude settings
├── .cursor/                     # Shelf-level Cursor settings
├── projects/                    # Project metadata & catalog
├── docs/                        # Cross-project documentation
│   ├── adr/                   # Architecture Decision Records
│   └── guides/                # How-to guides
├── scripts/                     # Cross-project scripts
├── governance/                  # Governance tooling
├── plans/                       # Work plans
└── [projects]                   # ~30 independent git repos
```

## Agent Workflow

1. **Identify the project** — Check the target project `README.md` or ask the user
2. **Navigate to project** — `cd <project-name>`
3. **Read project rules** — Check for `CLAUDE.md` or `AGENTS.md` in project
4. **Do the work** — Follow shelf rules in `AGENTS.md`
5. **Commit & push** — Use conventional commits, open PR if needed

## NOT AgilePlus

This shelf contains **many projects**, of which AgilePlus is one.
AgilePlus-specific documentation lives inside the `AgilePlus/` project directory,
not at shelf level.

The files that were previously here describing AgilePlus have been moved to
their correct locations:
- AgilePlus governance → `AgilePlus/GOVERNANCE.md`
- AgilePlus agent rules → `AgilePlus/AGENTS.md`
- AgilePlus README → `AgilePlus/README.md`

## Getting Help

- Shelf-level issues: Ask here
- Project-specific issues: `cd <project>` and check that project's docs
- Architecture decisions: `cat docs/adr/INDEX.md`
- General questions: Check the target project `README.md` first
