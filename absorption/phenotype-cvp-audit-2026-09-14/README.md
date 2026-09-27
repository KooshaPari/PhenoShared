HISTORICAL SNAPSHOT (2026-09-14): docs-3 is archived at docs/_archive/docs-3. Retained for traceability only; not current policy. Sibling audit: [phenotype-canonicalization/README.md](../phenotype-canonicalization/README.md)

# Phenotype CVP Audit - 2026-09-14

Fresh remote-GitHub pass against the 2026-09-11 movement audit.

Deliverables:
- `Phenotype_CVP_Audit_2026-09-14.pdf` - main report
- `Phenotype_CVP_Audit_2026-09-14.docx` - editable report
- `AGENT_CVP_EXECUTION_ADDENDUM.md` - copy/paste execution correction
- `cvp-snapshot.json` - machine-readable dated snapshot

The report distinguishes observed GitHub facts, repository/agent claims, engineering inferences, and local state that was not observable in this session.

## Snapshot Metrics

- **as_of**: 2026-09-14T16:37:00-07:00
- **baseline**: 2026-09-11 movement audit
- **scope**: remote GitHub + prior audit context; local worktrees not observed

| Metric | Value |
|--------|-------|
| current_repo_count_observed | 138 |
| repos_pushed_since_2026_09_12_observed | 101 |
| merged_prs_owned_estate_since_sep11_cutoff | 493 |
| merged_prs_authored_by_user_since_sep11_cutoff | 163 |
| civis_current_head_actions_total | 20 |
| civis_current_head_actions_success | 14 |
| civis_current_head_actions_failure | 6 |

## CVP Policy Floors

| Policy Key | Value |
|------------|-------|
| unit_floor | 0.85 |
| integration_floor | 0.85 |
| e2e_floor | 0.85 |
| mutation_floor_when_applicable | 0.85 |
| critical_obligations | 1.0 |
| macos_gui_requires_installed_app | true |
| default_tombstone_days | 60 |
| fork_network_delete_default | forbidden |

## Priority Queue

| Repo | State | Next |
|------|-------|------|
| Civis | CVP packaging active | installed Civis.app + full journey + QA floor |
| AgilePlus | desktop packaging active, assurance gaps self-identified | installed app + coverage/transport/perf/full E2E |
| sharecli | quality/polish active | packaged supervision journey + native coverage |
| Tracera | E2E/simplification improved; owner chat reportedly down | re-establish owner + deployable real datastore/auth journey |
| PhenoFabric | runtime/CI/bench/auth work active | real two-node composition proof |
| terminal-fabric | new active observability substrate | secure installable service + privacy/retention |
| BytePort/nanovms | dedup/migration active | consumer parity + restore/e2e proof |
| Portage | maintenance/gate-heavy | real evaluation CVP |
| PhenoLab | bench/lab active | clean reproducible benchmark bundle |
| hwLedger | quality gate repair active | install/probe/query product proof |
| PhenoMLX/hfscope | archived/tombstoned risk | preserve; verify successor + active sessions before deletion |
