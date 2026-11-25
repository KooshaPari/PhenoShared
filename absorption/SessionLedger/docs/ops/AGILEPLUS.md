# AgilePlus operations

SessionLedger uses the released AgilePlus CLI at:

```text
E:\agileplus-target\release\agileplus-cli.exe
```

The path can be overridden with `-CliPath` when running the repository scripts.
Run commands from the repository root because the `list-*` commands resolve
`.\agileplus.db` from the current working directory.

## Bootstrap

Create the ignored local SQLite database:

```powershell
.\agileplus\seed.ps1
```

Equivalent direct command:

```powershell
& 'E:\agileplus-target\release\agileplus-cli.exe' seed-requirements --db .\agileplus.db
```

The database is generated state and must not be committed. The released seeder
currently loads its bundled catalogs (six projects, six epics, and 150 stories
in the tested build), not `docs/functional_requirements.md`. Those records may
belong to AgilePlus, Tracera, and other bundled initiatives; they are useful
only as bootstrap data and must not be represented as SessionLedger backlog
items.

In the tested Windows release, `seed-requirements` populated the SQLite tables
but the `list-*` commands returned `No ... found.` from the same working
directory. This is a released-CLI read-path limitation, not proof that seeding
failed. Re-run with a newer compatible CLI before relying on listings.

## Inspect the backlog

Run the complete local workflow:

```powershell
.\scripts\agileplus-sync.ps1
```

Or inspect each level directly:

```powershell
$cli = 'E:\agileplus-target\release\agileplus-cli.exe'
& $cli list-projects
& $cli list-epics
& $cli list-epics --project <project-id>
& $cli list-stories
& $cli list-stories --epic <epic-id>
& $cli list-stories --status todo
```

Discover the project ID first, then scope epics to that project and stories to
the selected epic. Valid story statuses are `todo`, `in_progress`, `review`,
`done`, `blocked`, and `cancelled`.

## SessionLedger requirement mapping

When a SessionLedger project is available, create one AgilePlus story per
stable requirement ID. Keep the ID at the beginning of the story title and
copy its acceptance references from
[`docs/functional_requirements.md`](../functional_requirements.md).

| AgilePlus epic           | FR stories                             | Companion NFR stories                                                  |
| ------------------------ | -------------------------------------- | ---------------------------------------------------------------------- |
| Ingest and contracts     | FR-001, FR-002, FR-013                 | Lossless capture; schema compatibility and validation safety           |
| Browse and understand    | FR-003, FR-005, FR-007, FR-008, FR-010 | Bounded query latency; accessible and responsive desktop UI            |
| Replay and continue      | FR-004, FR-011, FR-012                 | Deterministic replay; crash-safe continuation and data integrity       |
| Lifecycle and operations | FR-006, FR-014, FR-015                 | Archive durability; service availability; telemetry and secret hygiene |

FR status maps to AgilePlus status as follows: `done` to `done`, `partial` to
`in_progress`, and `todo` to `todo`. NFR stories should cite measurable
acceptance evidence from the threat model, operational runbooks, tests, or
benchmarks. The bundled seeder cannot generate this SessionLedger mapping
today; it remains the target shape for a SessionLedger-specific catalog or
GitHub issues imported by sync.

## Optional GitHub sync

Sync is opt-in. Never put a token in the repository, command history, scripts,
or commits. Set all three variables only in the current process:

```powershell
$env:GITHUB_TOKEN = '<temporary token>'
$env:AGILEPLUS_PROJECT_ID = '<project-id>'
$env:AGILEPLUS_EPIC_ID = '<epic-id>'
.\scripts\agileplus-sync.ps1
Remove-Item Env:GITHUB_TOKEN
```

The script runs this operation only when all variables are present:

```powershell
& 'E:\agileplus-target\release\agileplus-cli.exe' sync KooshaPari/SessionLedger `
  --project $env:AGILEPLUS_PROJECT_ID `
  --epic $env:AGILEPLUS_EPIC_ID `
  --token $env:GITHUB_TOKEN
```

GitHub sync imports the repository surface supported by the CLI. It does not
by itself parse the FR table, infer NFRs, or replace acceptance evidence review.
