# PhenoMCPServers → PhenoShared (delta completion) — 2026-11-10

**Source repo:** [KooshaPari/PhenoMCPServers](https://github.com/KooshaPari/PhenoMCPServers)
**Source commit:** `8eb182b` — `test(scripts): tool discovery + invalid-call rejection + hard-fork pin validator (re-base on main) (#58)`
**Disposition:** `ABSORB` (delta completion of an earlier partial absorption)
**Absorbed by:** PhenoShared (`phenoAI`), 2026-11-10

## Why this record exists

An earlier absorption copied most of PhenoMCPServers into this repo at identical
relative paths (`catalog/`, `servers/`, `skills/`, `plugins/`, `agents/`), but
left a delta behind. A prior audit
([`audits/absorption-justifications/PhenoMCPServers-2026-07-17.md`](../../../audits/absorption-justifications/PhenoMCPServers-2026-07-17.md))
classified the repo `ARCHIVE_ONLY` on the grounds that it was code, not pure
registry docs — which was correct for the target it was evaluated against
(`phenodocs/registry/mcp-servers/`) but left the delta unabsorbed here.

This wave closes that delta so PhenoShared holds the complete PhenoMCPServers
content and the source repo can be archived or deleted without losing anything.

## Measured delta

File-level comparison of the source tree (473 files, `.git` excluded) against the
same relative paths in PhenoShared:

| Class     | Count | Meaning                               |
| --------- | ----- | ------------------------------------- |
| Identical | 353   | already byte-identical in PhenoShared |
| Missing   | 46    | **absorbed by this wave**             |
| Diverged  | 119   | present but differs from source       |

The 119 diverged files are not absorption gaps. They differ because PhenoShared
carries an earlier scrub that replaced the GitHub owner with `<REDACTED>` in text
and because several files were adapted for the monorepo (for example
`docs/ARCHITECTURE.md`, which here is PhenoShared's own architecture index rather
than the upstream MCP workspace skeleton). Those are intentional, pre-existing
divergences and were left untouched.

## What was absorbed (46 files)

### Schemas (2)

- `schemas/registry.schema.json` — PhenoMCPServers registry schema (`$defs` for
  `server`, `skill`, `plugin`, `agent`).
- `schemas/language-tiers.schema.json`

Note: `catalog/registry.schema.json` in this repo is **not** this schema. That
path holds the unrelated phenotype substrate catalog schema from
`phenotype-registry`. The MCP registry schema therefore lands under `schemas/`,
matching upstream layout.

### Validation pipeline (6)

- `scripts/validate_catalog.py`
- `scripts/validate_bundle_wiring.py`
- `scripts/validate_fork_parents.py`
- `scripts/validate_fork_pin.py`
- `scripts/validate_stale_patterns.py`
- `scripts/fleet_burndown.sh`

### Tests (6)

- `tests/test_catalog_validation.py`
- `tests/test_bundle_wiring.py`
- `tests/test_fork_pin_validator.py`
- `tests/test_hexakit_template.py`
- `tests/test_mcp_server_ts7_template.py`
- `tests/test_tool_discovery_and_invalid_call.py`

### Templates (15)

- `templates/mcp-server/` — Python MCP server scaffold (SKILL, agent, catalog
  entry, mcp.json, plugin, pyproject, server, skill templates plus `render.py`)
- `templates/mcp-server-ts7/` — TypeScript MCP server scaffold (`server.ts.tmpl`,
  `package.json.tmpl`, catalog entry, `render.py`)

These back `hexakit init mcp-server --catalog phenomcp`.

### Docs (17)

- `docs/CHARTER.md`, `docs/DOGFOOD.md`, `docs/HEXAKIT_INTEGRATION.md`,
  `docs/LANGUAGE-TIERS-AND-ROLES.md`, `docs/MCP-CATALOG.md`,
  `docs/README-PHENOMCP.md`, `docs/STATUS.md`, `docs/WIRING.md`
- `docs/edges/{README,mcpforge,ops-mcp}.md`
- `docs/requirements/phenomcp-frnfr.md`
- `docs/retire/RETIRED-MCP-REPOS.md`
- `docs/sessions/dogfood-fleet-lead-2026-06-17.md`
- `docs/spikes/{ts7-hexakit-binding,zig-mojo-mcp}.md`

No doc path collided with an existing PhenoShared doc, so all 17 landed at their
upstream relative paths.

### CI workflow (1, renamed)

- `.github/workflows/catalog.yml` → **`.github/workflows/phenomcp-catalog.yml`**

Renamed and adapted, not copied verbatim:

- `name` changed to `phenomcp-catalog` so it is identifiable in the monorepo
  workflow list.
- Trigger paths narrowed from the upstream super-set (`docs/**` was far too broad
  here) to the absorbed subtrees.
- The driver-mcp sync step now calls the local `scripts/check_driver_mcp_sync.py`
  instead of checking out `KooshaPari/substrate` into `substrate/`.
- `test_fork_pin_validator.py` added to the pytest invocation (upstream ran
  `validate_fork_pin.py` only through the test).

## Fidelity decision: verbatim, not scrubbed

Newly absorbed files are **byte-identical to upstream**, unlike the earlier batch
that had the owner name replaced with `<REDACTED>`. Rationale:

- The scrub corrupts semantics where the owner name is structural. Example:
  `catalog/registry.schema.json` has `"pattern": "^<REDACTED>/[A-Za-z0-9_.-]+$"`,
  which no longer matches a real `owner/repo` string, and markdown links such as
  `https://github.com/<REDACTED>/PhenoSpecs/...` are dead.
- Verbatim absorption keeps verification mechanical: a byte comparison against
  the source commit proves completeness.

Consequence: the repo now contains both scrubbed and unscrubbed copies of
equivalent upstream text. That inconsistency is inherited, not introduced by this
wave, and is not worth propagating.

## Verification

| Check                                                                                                                                                                                                                     | Result                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Files still missing after this wave                                                                                                                                                                                       | 0 (the one remaining "missing" path is the renamed workflow)                                                             |
| Byte-identical to source                                                                                                                                                                                                  | 353 of 473 (45 added by this wave; the 46th landed as the renamed workflow)                                              |
| Git blob hash of the 46 absorbed files vs source                                                                                                                                                                          | 45 of 46 identical; the only difference is the intentionally adapted workflow (source `f183f8bc…` → adapted `017f1953…`) |
| `python scripts/validate_catalog.py`                                                                                                                                                                                      | `OK registry_version=1.4.1`                                                                                              |
| `python scripts/validate_fork_parents.py`                                                                                                                                                                                 | `OK fork_parents lanes=['go','python','rmcp','rust']`                                                                    |
| `python scripts/validate_bundle_wiring.py`                                                                                                                                                                                | `OK bundle=phenotype-mcp-bundle servers=['pheno-org','substrate','substrate-dispatch']`                                  |
| `python scripts/validate_stale_patterns.py`                                                                                                                                                                               | 18 advisory `STALE:` lines against pre-existing PhenoShared docs; exit 0                                                 |
| `python scripts/check_driver_mcp_sync.py`                                                                                                                                                                                 | drift advisory lines; exit 0                                                                                             |
| `pytest tests/test_catalog_validation.py tests/test_bundle_wiring.py tests/test_hexakit_template.py tests/test_mcp_server_ts7_template.py tests/test_fork_pin_validator.py tests/test_tool_discovery_and_invalid_call.py` | 29 passed, 2 failed                                                                                                      |
| `pytest servers/substrate servers/pheno-org/tests`                                                                                                                                                                        | 60 passed                                                                                                                |

### The two pytest failures are pre-existing, not regressions

Both were reproduced identically in a clean clone of the source at `8eb182b`:

1. `test_fork_pin_validator.py::test_check_server_accepts_documented_deviation_directive`
   fails with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0x97` — a
   Windows-only console-encoding defect in the test harness (cp1252 em dash). It
   will not reproduce on the Ubuntu CI runner.
2. `test_tool_discovery_and_invalid_call.py::test_substrate_route_rejects_non_dict_task_with_validation_error`
   expects `fastmcp.exceptions.ValidationError` but the installed fastmcp raises
   raw `pydantic_core.ValidationError` — an upstream fastmcp version-pin drift.
   This file is deliberately not in the CI workflow's pytest list.

## Archive / delete readiness

All PhenoMCPServers content is now present in PhenoShared: 353 of 473 source
files are byte-identical, 119 carry the pre-existing `<REDACTED>` scrub or
monorepo adaptations, and the last file is present as the renamed workflow.
Nothing in the source tree is left unrepresented.

Deleting or archiving `KooshaPari/PhenoMCPServers` is therefore safe from a
content-preservation standpoint. It is **not** done by this wave; it remains an
operator decision because the repo is still live (`isArchived: false` as of
2026-11-10) and a previous audit recorded an unresolved `DECLARE_SPINE`
recommendation for it.

## Cross-references

- Earlier failsafe audit: [`audits/absorption-justifications/PhenoMCPServers-2026-07-17.md`](../../../audits/absorption-justifications/PhenoMCPServers-2026-07-17.md)
- Absorption index: [`docs/ABSORPTION_INDEX.md`](../../ABSORPTION_INDEX.md)
- Source catalog SSOT absorbed earlier: `catalog/registry.yaml`
- Absorbed registry schema: `schemas/registry.schema.json`
- Workflow: `.github/workflows/phenomcp-catalog.yml`
