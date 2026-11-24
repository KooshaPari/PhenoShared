# Phenotype Projects Control Plane

This folder is the stable runtime root for deterministic project materialization.

## Purpose

`phench` materializes repos from locked targets into
`Phenotype/projects/<target>/repos` and tracks lock metadata under
`Phenotype/projects/<target>/.phench`.

## Branch selection model

Each target repo entry stores `selected_ref` and `resolved_sha` under a lock.
Use feature branches directly by passing `--ref` when registering a repo into the target.

Example:

- `thegent phench target init my-stack`
- `thegent phench target add-repo my-stack --repo /abs/path/thegent --ref feature/next-wave`
- `thegent phench target lock my-stack`
- `thegent phench target materialize my-stack`
- `thegent phench run my-stack --repo-id thegent --command test`

## Module manifests and module composition

`Phenotype/projects/modules/<module>/manifest.json` is now the composition point for
module-wide target loading.

Each manifest supports:

- `repo_patterns`: Git checkout selection by repo ID glob.
- `default_ref`: Default ref for every matched repo (defaults to `HEAD`).
- `repo_ref_overrides`: Explicit refs by repo ID.
- `repo_runner_overrides`: Default runner by repo ID (for `run` when not provided).
- `repo_command_overrides`: Default command by repo ID.
- `repo_env_profile_overrides`: Default env profile by repo ID.

Use module import:

- `thegent phench target add-module <target> --module <module-name>`
- `--ref` can override the manifest `default_ref` for every included repo.
- `--exclude` removes exact repo IDs from manifest selection.

Recommended pattern:

- `thegent phench target init <target>`
- `thegent phench target add-module <target> --module thegent-app --ref feature/next`
- `thegent phench target add-module <target> --module thegent-control-plane`
- `thegent phench target lock <target>`
- `thegent phench target materialize <target>`
- `thegent phench env profile-set <target> --profile ci --var PYTEST_ADDOPTS=-q --var RUNNER=ci`
- `thegent phench run <target> --repo-id thegent --runner task --command test`

## Runner and profile contract

- Commands are run through detected runners (`task|just|make|pnpm|npm|bun`).
- Environment overlays are controlled by profiles at
  `Phenotype/projects/<target>/.phench/env-profiles.json`.
- You can set profiles with:
  - `thegent phench env profile-set <target> --profile <name> --var KEY=VALUE`

### Module override precedence

When running a target, effective values are selected in this order:

1. CLI flag (`--runner`, `--command`, `--env-profile`) on `run`.
2. Module-injected values stored in lock (`selected_runner`, `selected_command`, `selected_env_profile`) from `add-module`.
3. Repo default from manifest when added via module.
4. Target active profile for `env` fallback if nothing else is set.

Profile precedence for `--env-profile`:

- `--env-profile` on `run` always wins.
- Otherwise lock entry `selected_env_profile` wins.
- Otherwise the target active profile is used.

### `--all-repos` and safety

- Without `--all-repos`, `run` executes the first materialized repo only.
- With `--all-repos`, every repo in target runtime is used.
- `--all-repos` requires explicit command configuration (`--runner` + `--command`) unless each repo has module-level overrides in lock.
- Recommended safety pattern:
  - Use `--all-repos` only after `target lock` and `target materialize`.
  - Add modules separately per domain (`--module thegent-app`, then `--module thegent-control-plane`) to avoid broad selectors.

## Module manifest guidance

Each manifest must include:

- `schema_version`: integer contract marker.
- `repo_patterns`: repo ID glob list from `Phenotype/projects/repos`.
- `default_ref`: fallback ref for all matched repos.
- `repo_ref_overrides`: optional per-repo `ref`.
- `repo_runner_overrides`: optional per-repo `runner`.
- `repo_command_overrides`: optional per-repo `command`.
- `repo_env_profile_overrides`: optional per-repo `profile`.

Default repo exclusion is always enforced for:
`4sgm`, `parpour`, `civ`, `trace` plus any `--exclude` values.

## Extension points for control-plane/execution modules

Treat the following module manifests as deployment boundaries:

- `thegent-control-plane`: all repos for policy, orchestration, and CLI governance.
- `thegent-execution`: runtime engines, wrappers, build/run pipelines, and execution adapters.
- `thegent-mcp`: model/connectivity tooling and MCP integration repos.
- `thegent-governance`: policy, standards, and repository-wide conventions.
- `thegent-app`: operator-facing and application orchestration repos.

Recommended module manifest template for an execution-heavy module:

```json
{
  "schema_version": 1,
  "repo_patterns": ["portage*", "helios*", "agentapi*", "cliproxyapi*"],
  "default_ref": "HEAD",
  "repo_ref_overrides": {
    "portage": "main",
    "heliosCLI": "main"
  },
  "repo_runner_overrides": {
    "portage": "task",
    "heliosCLI": "task"
  },
  "repo_command_overrides": {
    "portage": "test",
    "heliosCLI": "test"
  },
  "repo_env_profile_overrides": {
    "portage": "ci",
    "heliosCLI": "ci"
  }
}
```

Use wildcard selectors for broad composition, then narrow with `--exclude` as needed.

## Environments

- Default project root: `$HOME/CodeProjects/Phenotype/projects`
- Override with `THGENT_PHENOTYPE_ROOT`.
- Mirror sync root: `$HOME/.cache/thegent-phench`.
- Override mirror with `THGENT_PHENCH_HOME_ROOT`.

## Runtime status and drift

Use these for health checks:

- `thegent phench status <target>`
- `thegent phench sync <target>`

## Workspace-wide module discovery

Use this command to find overlap before creating new module manifests:

- `thegent phench scan-shared-repos --repos-root <path> --min-repos 2`
- Optional flags:
  - `--exclude <repo-id>` (repeatable)
  - `--candidates` to include manifest-shaped candidate output
  - `--min-repos <N>` to report only modules seen in `N` or more repos

Example:

```bash
thegent phench scan-shared-repos \
  --repos-root "$THGENT_PHENOTYPE_ROOT/repos" \
  --exclude civ \
  --exclude trace \
  --min-repos 2 \
  --candidates
```

## Governance notes

This workspace is repository-local, but lock files and metadata are intentionally
portable and can be moved between machines for reproducible replays.
