# CLI & API Remediation — Audit Gap C-API (57%)

> **Scope:** `agileplus` CLI ergonomics, exit-code contract, `--json` output shape, versioning policy, and quick-win polish notes.  
> **Binary:** `crates/agileplus-cli` → `agileplus` (also invokable as `agileplus-cli` in tests).

## Command surface overview

```
agileplus [--db PATH] <SUBCOMMAND>

Subcommands (top level):
  feature    Module/cycle CRUD + search
  module
  cycle
  status     Project summary (mock store)
  version    Print CLI version (duplicate of -V/--version)
  sync       GitHub ↔ AgilePlus sync
  seed-requirements
  list-projects | list-epics | list-stories
  trace      link | list | show
  dashboard  DAG / kanban view (--json supported)
  worklog    validate | convert | schema | list
```

Global flags today:

| Flag | Env | Default | Notes |
|------|-----|---------|-------|
| `--db PATH` | `AGILEPLUS_DB` | `./agileplus.db` | SQLite location |
| `-h, --help` | — | — | clap-generated per subcommand |
| `-V, --version` | — | `CARGO_PKG_VERSION` | Workspace `0.1.0` |

---

## Exit code contract

| Code | Meaning | Examples |
|------|---------|----------|
| **0** | Success | Command completed; validation passed |
| **1** | User/runtime error | `anyhow` error bubbled to `main`; missing entity; DB open failure |
| *(reserved)* **2** | Usage / argv error | *Not consistently used today* — clap may exit 2 on parse errors before `main` |
| *(reserved)* **3** | Policy / gate failure | *Future:* `gate run`, `specs audit --strict` |

**Current implementation** (`crates/agileplus-cli/src/main.rs`):

```rust
if let Err(e) = result {
    eprintln!("error: {e:#}");
    std::process::exit(1);
}
```

**Remediation targets:**

1. Document reserved codes in `--help` footer (additive `long_about` string).
2. Map validation failures that are *expected* (e.g. worklog schema) to exit **3** instead of **1** where scripts branch on outcome.
3. Ensure `--json` error responses include `"ok": false` on stdout *and* non-zero exit (see below).

Subcommands with independent `exit(1)` today: `worklog`, `gate_run` — align with global contract in a follow-up.

---

## `--json` output contract

### Commands with `--json` today

| Command | Flag | Schema |
|---------|------|--------|
| `dashboard` | `--json` | Structured dashboard payload (`serde` types in `dashboard.rs`) |
| `specs audit` | `--json` | Audit findings array (integration tests) |
| `frontend audit` | `--json` | Strict audit mode |

### Recommended standard envelope (all JSON commands)

```json
{
  "ok": true,
  "version": "0.1.0",
  "command": "dashboard",
  "data": { }
}
```

On error:

```json
{
  "ok": false,
  "version": "0.1.0",
  "command": "trace link",
  "error": {
    "kind": "not_found",
    "message": "entity wp:99 not found"
  }
}
```

**Rules:**

- JSON goes to **stdout**; human tables to stdout without `--json`.
- Diagnostics / tracing to **stderr**.
- Stable field names across minor versions; additive fields only.
- Include `"version"` for automation pinning.

### `dashboard --json` (reference)

Emits WP state counts, recent worklog rows, recent events, and trace-link summary grouped by `link_type`. Use for CI snapshots:

```bash
agileplus dashboard --db ./agileplus.db --json | jq '.trace_links'
```

### `trace` subcommands (gap)

`trace link|list|show` are **text-only** today. Remediation: add `--json` mirroring `dashboard` link section.

---

## Subcommand ergonomics

### Naming consistency

| Pattern | Examples | Recommendation |
|---------|----------|----------------|
| `list-*` kebab | `list-projects`, `list-epics` | Keep; document in cheatsheet |
| Nested `feature list` | `agileplus feature list` | Keep for domain grouping |
| Duplicate version | `agileplus version` vs `-V` | Deprecate subcommand in help text; prefer `-V` for scripts |

### Entity reference format

`trace` commands use `<kind>:<id>` (e.g. `wp:42`, `feature:7`). Document in `agileplus trace --help` examples block (additive clap `after_help`).

### Global `--json` (future)

Proposed global flag on root `Cli` struct:

```rust
#[arg(long, global = true)]
json: bool,
```

Dispatch layer selects `OutputFormat::Json | Human` — reduces per-command drift.

---

## Versioning policy

| Artifact | Source | Policy |
|----------|--------|--------|
| CLI `--version` | `CARGO_PKG_VERSION` / workspace `0.1.0` | Semver; bump minor for additive CLI flags |
| JSON `"version"` field | Same as CLI | Must match for a given binary |
| `SENTRY_RELEASE` | `CARGO_PKG_VERSION` or env override | See `.env.example` |
| API `/info` | Server crate version | Independent; clients should not assume parity with CLI |

**Pre-1.0:** breaking JSON field renames allowed only with `"schema_version": 2` bump and changelog entry.

### `--version` / `--help` polish (quick wins — doc-only in this PR)

The clap `Parser` already sets `version` and `arg_required_else_help = true`. Recommended polish (code follow-up):

1. **Root long about:**
   ```
   AgilePlus — spec-driven project management CLI.
   Environment: AGILEPLUS_DB (default ./agileplus.db)
   Docs: docs/remediation/CLI_API.md
   ```
2. **`version` subcommand:** print same string as `-V` **plus** git SHA when `AGILEPLUS_BUILD_SHA` is set (CI).
3. **`--help` footer:** print exit-code table (section above).
4. **Hidden alias:** `-v` → `--version` (clap `short = 'v'` on version flag) — *only if no conflict with verbose*.

Smoke tests already assert version output (`crates/agileplus-cli/tests/cli_smoke.rs::version_prints_known_prefix`).

---

## HTTP API cross-reference

CLI commands that mirror API resources:

| CLI | API route (typical) |
|-----|---------------------|
| `list-projects` | `GET /projects` |
| `list-epics` | `GET /epics` |
| `list-stories` | `GET /stories` |
| `sync` | GitHub sync use-case (application layer) |

Auth: API uses `X-API-Key` (`AGILEPLUS_API_KEY`). CLI local mode uses SQLite directly — no API key required.

---

## Scripting examples

```bash
# Fail CI on any error
set -euo pipefail

agileplus --db ./agileplus.db dashboard --json > dashboard.json
jq -e '.ok == true' dashboard.json >/dev/null 2>&1 || { echo "dashboard failed"; exit 1; }

# Entity link (human output today)
agileplus trace link wp:1 feature:2 --link-type implements --note "smoke"
```

---

## Remediation checklist

- [ ] Standard JSON envelope across `dashboard`, `trace`, `list-*`
- [ ] Global `--json` + `--format json|table`
- [ ] Exit code 2/3 reserved paths documented in clap `long_about`
- [ ] `version` subcommand emits build metadata in CI
- [ ] OpenAPI / utoipa spec linked from `agileplus api --help` (when exposed)

---

## References

- `crates/agileplus-cli/src/main.rs` — dispatch + exit handling
- `crates/agileplus-cli/src/commands/dashboard.rs` — `--json` reference impl
- `crates/agileplus-cli/src/commands/trace.rs` — entity ref format
- `crates/agileplus-cli/tests/cli_smoke.rs` — version smoke test
- `docs/remediation/OPS.md` — `AGILEPLUS_*` environment variables
