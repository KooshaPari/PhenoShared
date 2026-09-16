# Tracera dual-write rollout runbook (v0.13 Phase 1 tasks 12, 13, 16)

**Status:** DRAFT — v0.13 Phase 1, tasks 12 + 13 + 16 combined.
**Audience:** on-call engineers rolling out dual-write to staging and prod.
**Owner:** forge (pheno-harness) <forge@phenotype.local>

## TL;DR

Tracera dual-write is now gradable per environment via
`trace_bridges.cohort_policies` and the `PHENO_ENV` env var. The
default behavior is preserved when `dual_write=False` is explicit in
the runtime config or the operator never sets `PHENO_ENV`. The rollout
follows a 3-stage cohort:

| Stage | `PHENO_ENV` | cohort | `dual_write` | `sample_rate` | audience |
|-------|-------------|--------|--------------|---------------|----------|
| 0 | unset (dev) | dev | `false` (default) | 1.0 | local development |
| 1 | `staging` | staging | `true` | 1.0 | CI + staging fleet |
| 2 | `prod` | prod | `true` | 1.0 | production (post-validation) |

`dual_write_sample_rate` is provided for partial rollouts (e.g.
`0.1` = 10% cohort). Sample-rate skips are recorded in
`bridge.skipped_sample` and surface as `tracera:sampled_out` hooks
for test introspection.

## How the rollout flag flows

```
PHENO_ENV
  ↓
pheno.runtime_config.active_environment()
  ↓
trace_bridges.cohort_policies[<env>]   ← "on" or "off"
  ↓
tracera_bridge.TraceraBridge.active_cohort()
  ↓
operator decision (deploy / rollback / partial sample)
```

## Stage 0 — dev (default)

No environment variable required. Default behavior is dual-write
**off** unless overridden in `config/dev.yaml`. Operators may set
`dual_write: true` in dev to validate Tracera connectivity without
sending production traffic.

```sh
# Default
unset PHENO_ENV
.venv/bin/python -c "from traces.tracera_bridge import TraceraBridge; print('ok')"

# Override locally
PHENO_ENV=staging .venv/bin/python -c "
from pheno.runtime_config import load_config, active_environment
cfg = load_config()
print('env=', cfg.trace_bridges.active_environment)
print('cohort=', cfg.trace_bridges.cohort_policies[cfg.trace_bridges.active_environment])
print('dual_write=', cfg.trace_bridges.dual_write)
"
```

## Stage 1 — staging rollout

1. Deploy `v0.13` build to staging fleet (see `docs/CHANGELOG.md`).
2. Set `PHENO_ENV=staging` on staging hosts (systemd env file or
   launchd `EnvironmentVariables`).
3. Restart pheno-harness service. `tracera_bridge` reads the cohort
   policy from `config/staging.yaml` and enables dual-write.
4. Validate via `tracera://history` MCP resource (24h rolling) and
   the `summary://fleet` dashboard.
5. Monitor error rate for 24h. Threshold: < 5% (alert fires per task
   18 of v0.13 Phase 1).

```sh
# On staging host
PHENO_ENV=staging .venv/bin/python scripts/cron/snapshot_sota.py
PHENO_ENV=staging .venv/bin/python -m pytest -q tests/trace_store/
```

## Stage 2 — production rollout

1. Validate Stage 1 for ≥ 7 consecutive days (per ADR 010 release
   cadence).
2. Open a `release/v0.13-pheno-harness-summit` branch.
3. Set `PHENO_ENV=prod` on production hosts (one host at a time).
4. Validate per-host: `tracera://history` shows new events for that
   host's session_id; `summary://fleet` aggregates them.
5. Roll forward one host at a time; if error rate > 5%, roll back
   that host (see Rollback procedure below).

```sh
# Per-host enable (canary)
PHENO_ENV=prod .venv/bin/python scripts/cron/snapshot_sota.py
PHENO_ENV=prod .venv/bin/python -c "
from pheno.runtime_config import load_config
cfg = load_config()
print('prod dual_write=', cfg.trace_bridges.dual_write)
print('prod sample_rate=', cfg.trace_bridges.dual_write_sample_rate)
"
```

## Sample-rate cohort (partial rollout)

When full dual-write is too risky, set a sample rate:

```sh
# Send only 10% of events to Tracera
TRACERA_DUAL_WRITE_SAMPLE_RATE=0.1 PHENO_ENV=prod .venv/bin/python <cmd>

# Or in config:
# trace_bridges:
#   dual_write: true
#   dual_write_sample_rate: 0.1
```

Each event is independently sampled via `random.random()` against
`sample_rate`. Events skipped are recorded as `bridge.skipped_sample`
and emitted as `tracera:sampled_out` hooks (for test introspection).

Sample rate resolution order (highest priority first):
1. Explicit `sample_rate=` constructor arg on `TraceraBridge(...)`.
2. `TRACERA_DUAL_WRITE_SAMPLE_RATE` env var.
3. `trace_bridges.dual_write_sample_rate` in the runtime config.

## Cohort policies

Cohort policies are defined in `config/pheno_runtime.yaml` under
`trace_bridges.cohort_policies`. They map env name → "on"/"off"
(or any string the operator chooses).

```yaml
cohort_policies:
  dev: "off"
  staging: "on"
  prod: "on"
```

The bridge exposes `bridge.active_cohort()` returning the policy for
the active env. Default for unknown envs is "off".

## Rollback procedure (task 13)

If dual-write is causing Tracera outages or the bridge is failing
unsafe:

1. **Disable dual-write globally** (fastest path):
   ```sh
   # Override the env to off, regardless of cohort policy
   TRACERA_DUAL_WRITE_DEFAULT=false PHENO_ENV=prod .venv/bin/python <cmd>
   # Or set trace_bridges.dual_write: false in the runtime config
   ```

2. **Per-host rollback**: unset `PHENO_ENV` on the affected host.
   The default `dev` cohort is `off`, so the bridge reverts to
   JSONL-only writes.

3. **Full rollback**: revert the deploy to the previous `v0.12`
   release. The `dual_write_default` field is opt-in (off by
   default), so reverting never re-enables dual-write.

4. **Verify rollback**:
   ```sh
   PHENO_ENV=prod .venv/bin/python -c "
   from pheno.runtime_config import load_config
   cfg = load_config()
   assert cfg.trace_bridges.dual_write is False
   print('rollback verified: dual_write=False')
   "
   ```

5. **Open incident**: link the `summary://fleet` dashboard capture
   from the failure window. Notify in #phenotype-ops Slack channel.

## Observability

| Resource | Purpose |
|----------|---------|
| `tracera://history` | 24h Tracera event history (5-min tick) |
| `summary://fleet` | One-stop fleet dashboard aggregating bridge, tailscale, tests, history |
| `tracera-watch` daemon | Detects Tailscale daemon failures (3-method detection) |
| `bridge.health()` | Bridge-level introspection (events emitted, sampled, errored) |
| `traces/ingest.py` logs | JSONL sink path; permanent record of every event |

## Verification commands

```sh
# Test the rollout pipeline without committing
.venv/bin/python -m pytest -q tests/test_tracera_dual_write_sample.py

# Inspect active config
.venv/bin/python -c "
from pheno.runtime_config import load_config, active_environment
cfg = load_config()
print(f'env={active_environment()}')
print(f'dual_write={cfg.trace_bridges.dual_write}')
print(f'sample_rate={cfg.trace_bridges.dual_write_sample_rate}')
print(f'cohort={cfg.trace_bridges.cohort_policies[cfg.trace_bridges.active_environment]}')
"

# Verify env-var overrides
TRACERA_DUAL_WRITE_SAMPLE_RATE=0.1 .venv/bin/python -c "
from pheno.runtime_config import load_config
cfg = load_config()
assert cfg.trace_bridges.dual_write_sample_rate == 0.1
print('env override ok')
"
```

## References

- `pheno/runtime_config.py` — `TraceBridgesConfig`, `active_environment()`
- `traces/tracera_bridge.py` — `TraceraBridge._sample_rate`, `active_cohort()`
- `config/pheno_runtime.yaml` — schema_version=2
- `config/{dev,staging,prod}.yaml` — per-env overrides
- `tests/test_tracera_dual_write_sample.py` — 22 unit tests
- v0.13 WBS-PERT-100 tasks 6, 7, 8, 9, 10, 12, 13, 15, 16

---

*Runbook + rollback + cohort policies (tasks 12 + 13 + 16).*
