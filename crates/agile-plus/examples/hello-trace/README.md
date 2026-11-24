# hello-trace — minimal end-to-end AgilePlus + Tracera walkthrough

This example shows, in under five minutes, how a tiny GitHub issue becomes a
traceable record inside AgilePlus and a linked entry in Tracera. It is the
smallest "hello world" that exercises the real `agileplus-cli` binary, the
seeded FR/NFR catalogs, and the JSON project listing the CLI already exposes.

The walkthrough is intentionally local: no GitHub token, no remote sync, no
network. The point is to prove the on-disk pipeline works, not to validate a
production deployment.

## Why this exists

New contributors to the Phenotype org need one reproducible path that:

1. Shows the CLI is built and the workspace links to a real database.
2. Proves the FR/NFR seed ingests a real catalog and is idempotent.
3. Demonstrates the JSON output contract used by downstream agents.

Without it, the first run takes ~20 minutes of grepping the workspace and
guessing which subcommand to try first.

## Prerequisites

- Rust toolchain pinned in `rust-toolchain.toml` (nightly at time of writing).
- The workspace builds: `cargo build --workspace` (or `cargo build -p agileplus-cli` for the fast path).
- No secrets required; everything runs offline against an empty SQLite file.

## Walkthrough

```bash
# 1. Build the CLI (one-time, ~3 minutes cold).
cargo build -p agileplus-cli

# 2. Create a fresh, empty database in a scratch directory.
SCRATCH=$(mktemp -d)
DB="$SCRATCH/agileplus.db"
rm -f "$DB"

# 3. Seed the FR/NFR catalogs as Epics + Stories.
#    This is the same path the GitHub sync uses, minus the network.
#    `--db` is supported on seed-requirements and writes to the chosen path.
./target/debug/agileplus-cli seed-requirements --db "$DB" --verbose

# 4. cd into the scratch dir so the list-* subcommands find the DB at
#    the default `./agileplus.db` path they read from.
cd "$SCRATCH"
cp "$DB" ./agileplus.db

# 5. List the projects that landed in the database, in JSON form.
./target/debug/agileplus-cli list-projects --json | head -40

# 6. List the epics, filtered by project (use the ID from step 5).
./target/debug/agileplus-cli list-epics --project 1 | head -20

# 7. List one story, demonstrating the FR/NFR traceability tag is present.
./target/debug/agileplus-cli list-stories --epic 1 | head -20
```

Each command exits 0 on success; non-zero exit codes are described under
"Exit codes" below.

## Exit codes

The CLI follows the standard convention so scripts and dispatch agents can
react without parsing stdout:

| Code | Meaning |
| ---- | ------- |
| 0    | Success — query or seed completed and stdout is valid for the chosen format. |
| 1    | Generic error — see stderr for context (e.g. database file missing, schema drift). |
| 2    | Invalid arguments — the `clap` parser rejected the flag set; rerun with `--help`. |
| 3    | I/O error — SQLite open or read failed (permissions, disk full, locked). |
| 4    | Catalog parse error — the embedded FR/NFR markdown could not be parsed; do not retry, file a bug. |

If you see code 1, 3, or 4, the database may be in a half-initialised state;
delete the file and re-run `seed-requirements` before retrying.

## What the seed actually produces

The `seed-requirements` subcommand ingests six catalogs
(`docs/requirements/{agileplus,tracera,phenotype-voxel,authvault,phenomcp,phenoobservability}-frnfr.md`)
and turns each one into:

- A `Project` row (one per catalog).
- An `Epic` row per top-level section in the catalog.
- A `Story` row per FR/NFR item, with a `tracera_id` field linking it back to
  the source requirement ID (e.g. `FR-AGP-001`).

The exact JSON shape is documented in `crates/agileplus-cli/src/commands/list_projects.rs`
and the seed source lives in `crates/agileplus-sqlite/src/seed.rs`.

## Reverting the example

This example ships only `README.md`, `smoke.sh`, and the catalogues it reads
are already versioned. To roll it back, delete the directory and the CLI
behaviour is unchanged:

```bash
git rm -r examples/hello-trace
```

## UX research question

- What is the smallest first run that gives a new contributor confidence the
  local toolchain + database + CLI round-trip works end to end? This example
  targets ~5 minutes; if your first PR took longer, file a follow-up.
