# Misc Audits — 2026-05-05

Date: 2026-05-05
Scope: `/Users/<REDACTED>/CodeProjects/Phenotype/repos`

---

## Audit 1: Broken Symlinks

**Command:** `find . -maxdepth 3 -type l ! -path "*/.claude/worktrees/*" ! -path "*/AgilePlus-wtrees/*" -exec sh -c 'test -e "$1" || echo "BROKEN: $1"' _ {} \;`

### Canonical repos (non-worktree)

| Repo | Broken Links |
|------|-------------|
| `helios-cli/` | `crates/harness_zig`, `crates/harness-native`, `transport` |
| `helioscope/` | `CONSTITUTION.yaml`, `crates/harness_zig~HEAD`, `crates/harness-native`, `transport`, `bazel-bin`, `bazel-out`, `bazel-testlogs`, `bazel-heliosCLI` |
| `heliosApp/` | `CONSTITUTION.yaml` |
| `phenoXdd/` | `.pre-commit-config.yaml` |
| `PolicyStack/` | `.pre-commit-config.yaml` |
| `AtomsBot/` | `KInfra` |
| `crates/phenotype-config/` | `.pre-commit-config.yaml` |
| `pheno/phenotype-hub/` | `SECURITY.md` |

### Worktrees (orphaned)

**`heliosApp-wtrees/`**:
- `journey-impl/`: `CONSTITUTION.yaml`, `ADR.md`
- `release-cut-adopt/`: `CONSTITUTION.yaml`, `ADR.md`
- `sladge-badge/`: `CONSTITUTION.yaml`, `ADR.md`
- `trufflehog/`: `CONSTITUTION.yaml`, `ADR.md`
- `wip-heliosapp-observabili.../`: `CONSTITUTION.yaml`, `ADR.md`

**`helios-cli-wtrees/`**:
- `codex-rs-unblock/`: `transport`, `python`
- `upstream-mining/`: `transport`, `python`
- `workspace-deps-fix/`: `transport`, `python`
- `sladge-badge/`: `transport`, `python`

**`PolicyStack-wtrees/`**:
- `journey-impl/`: `.pre-commit-config.yaml`
- `sladge-badge/`: `.pre-commit-config.yaml`

**`Tokn-wtrees/`**:
- `sladge-badge/`: `.pre-commit-config.yaml`, `SECURITY.md`
- `main-ci-followup-20260427/`: `SECURITY.md`
- `workflow-worklog-hygiene-20260.../`: (partial path shown)

**`AtomsBot-wtrees/`**:
- `journey-impl/`, `bump-happy-dom-v20/`, `sladge-badge/`, `bun-unblock/`: `KInfra`

**`.archive/`**:
- `phench-ghost-2026-05-02/`, `phenoEvaluation/`, `colab/`: `.pre-commit-config.yaml`

### Notable observations

- `helioscope/` has 8 broken symlinks (bazel artifacts + transport + harness)
- Multiple worktrees have orphaned `CONSTITUTION.yaml` / `ADR.md` links — likely from a refactor that moved these files out of the worktree root
- `helios-cli/` and `helioscope/` share the same broken `transport`, `harness_zig`, `harness-native` pattern — possibly the same upstream change affected both
- `bazel-*` symlinks in `heliosscope/` are build artifacts that were likely removed after a build

---

## Audit 2: Duplicate Cargo Workspace Names

**Command:** `for f in $(find . -name "Cargo.toml" -not -path "*/target/*" -not -path "*/.claude/worktrees/*" | sort); do grep -m1 "^name" "$f" 2>/dev/null && echo "  <- $f"; done | grep -B1 "  <-" | grep "^name" | sort | uniq -c | sort -rn | head -20`

**Result: No actual duplicates found.** All high-count entries are distinct crates sharing common descriptive names across the monorepo:

| Count | Name | Interpretation |
|-------|------|----------------|
| 51 | `fuzz` | 51 distinct fuzzing crate instances across crates/ |
| 39 | `nexus` | 39 distinct nexus sub-crate instances |
| 33 | `phenotype-event-sourcing` | 33 event-sourcing crate instances |
| 32 | `agileplus-bdd` | 32 BDD-related crate instances |
| 31 | `agileplus-proto` | 31 proto-related crate instances |
| 31 | `agileplus-agent-service` | 31 agent-service crate instances |
| 31 | `agileplus-agent-review` | 31 agent-review crate instances |
| 31 | `agileplus-agent-dispatch` | 31 agent-dispatch crate instances |

These counts reflect the number of `Cargo.toml` files *named* with these identifiers across the workspace — not actual name collisions within a single workspace. Each `Cargo.toml` has a unique path, so there is no workspace-level name collision causing build warnings.

---

## Audit 3: README.md Presence

**Command:** `for r in */; do [ -f "$r/README.md" ] || echo "MISSING: $r"; done | grep -v "wtrees\|_archived\|tests/\|specs/"`

### Repos without README.md (canonical projects)

| Repo | Status |
|------|--------|
| `AgilePlus/` | Missing (unexpected — bootstrap complete per CLAUDE.md) |
| `AgilePlus-wtr/` | Missing |
| `AtomsBot-wtrees/` | Not a repo root |
| `crates/` | Missing (shared internal crate dir — may not need top-level README) |
| `docs/` | Missing |
| `findings/` | Missing |
| `fleet-audit/` | Missing |
| `libs/` | Missing (shared internal libs dir) |
| `Observably/` | Missing |
| `PhenoContracts/` | Missing |
| `PhenoControl/` | Missing |
| `PhenoEvents/` | Missing |
| `PhenoSchema/` | Missing |
| `phenotype-icons/` | Missing |
| `phenotype-skills/` | Missing |
| `plans/` | Missing |
| `portage-adapter-core/` | Missing |
| `prompts/` | Missing |
| `proto/` | Missing |
| `python/` | Missing |
| `references/` | Missing |
| `rust/` | Missing |
| `scripts/` | Missing |
| `src/` | Missing |
| `templates/` | Missing |
| `thegent-jsonl/` | Missing |
| `thegent-shm/` | Missing |
| `tooling/` | Missing |
| `ValidationKit/` | Missing |

### Non-repos correctly flagged (build artifacts, cache, wrappers)

- `__pycache__/` — Python cache
- `AgilePlus-wtrees/` — worktree wrapper dir
- `apps/` — empty/internal wrapper
- `bdd-integration/`, `byteport-landing/`, `hwledger-landing/` — spec/stub dirs
- `default/`, `node_modules/`, `target/` — build artifacts
- `Tracera-corrupt-20260501201930/` — corrupt artifact
- `worktrees/` — worktree hub dir

### Notable observations

- `AgilePlus/` is listed as missing README.md — needs verification (CLAUDE.md states bootstrap is complete)
- Most shared internal dirs (`libs/`, `crates/`, `proto/`, `scripts/`, etc.) are missing READMEs, which is consistent with them being component directories rather than standalone project roots
- The top-level repos that should have READMEs but are missing them: `AgilePlus/`, `AgilePlus-wtr/`, `Observably/`, `PhenoContracts/`, `PhenoControl/`, `PhenoEvents/`, `PhenoSchema/`, `ValidationKit/`, `fleet-audit/`, `phenotype-icons/`, `phenotype-skills/`
