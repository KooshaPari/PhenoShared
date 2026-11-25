# Audit justification: pheno-control-plane — PARTIAL_ARCHIVE (in-progress)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-control-plane-audit20260901` (NEW)
**Decision**: PARTIAL_ARCHIVE — staged for absorb into phenotype-fleet-ops

## Audit findings

1. **Never absorbed on remote**: zero commit/PR/branch references across all
   candidate target repos (phenotype-fleet-ops, phenotype-hub, helios-cli,
   pheno). The source repo was archived but no absorb PR was ever opened.

2. **No registry row as of 2026-07-18 freeze**: this source had zero
   registry footprint. New row `repo-pheno-control-plane-audit20260901`
   (registry v1.6.83) closes the gap.

3. **Source content (14 files, 20 KB)**:
   - `podman/docker-compose.yml` — full stack (NATS, Postgres, MinIO, Cockpit)
   - `bridge/publish_status.py` — status bridge
   - `docs/ARCHITECTURE.md` — architecture narrative
   - plus 11 supporting files (Dockerfiles, configs, README, LICENSE)

4. **Visibility was private**: operator-only repo, now archived.

## Planned absorb target

**`phenotype-fleet-ops/agent-devops-setups/tailnet-control-plane/`**

Rationale:
- `phenotype-fleet-ops/agent-devops-setups/` already houses multi-service
  stacks (cockpit, gateway, etc.) with the same pattern (podman compose
  + bridge scripts + docs/ARCHITECTURE.md).
- `tailnet-control-plane/` is a natural sibling to the existing
  `cockpit-control-plane/`, `gateway-control-plane/` etc. setups.

## State captured

| Aspect | State at audit |
| --- | --- |
| size_kb | 20 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-08 |
| archived_at | 2026-08-08 |
| visibility | private (now public via archive) |

## Forward-looking note

**HOLD — not DELETE-SAFE**. The source has never been absorbed. A new PR
is required to land the source content into
`phenotype-fleet-ops/agent-devops-setups/tailnet-control-plane/` before
the GH source can be deleted.

PR scope (planned):
- Move 14 source files into
  `phenotype-fleet-ops/agent-devops-setups/tailnet-control-plane/`
- Adapt podman-compose service names to fleet-ops conventions
- Update fleet-ops `docs/ECOSYSTEM_MAP.md` with new setup reference
- Update registry row to ABSORB + fsm=deleted + deleted_at
- Update registry row with target + pr fields

Estimated effort: 2 hours (manual content review + fleet-ops conventions).

## References

- target row: `repo-pheno-control-plane-audit20260901` (registry v1.6.83, NEW)
- planned target: `phenotype-fleet-ops/agent-devops-setups/tailnet-control-plane/`
- sibling setups: `phenotype-fleet-ops/agent-devops-setups/cockpit-control-plane/`,
  `phenotype-fleet-ops/agent-devops-setups/gateway-control-plane/`
