# Crate Relocation Runbook

**Repo:** HexaKit  
**Scope:** Move domain crates/modules from HexaKit to canonical domain repos per [DISPOSITION.md](../boundary/DISPOSITION.md)  
**Plan:** Ecosystem Disposition DAG v3 — Phase 2 waves  
**Related:** [Harness API](../contracts/harness-api.md), [Lane descriptor schema](../contracts/lanes/schema.json), [WORKTREES.md](../../WORKTREES.md)

This runbook is the standard procedure for every **MUTATE_RELOCATE** disposition lane. One lane = one bounded relocation; do not batch unrelated crates in a single PR.

---

## Preconditions

- Disposition row exists in `phenotype-registry/registry/disposition-index.json` and FSM state is **`ready`** (or **`claimed`** by this lane).
- Chokepoint dependents listed in `registry/chokepoints.json` are green for the target domain.
- Worktree created per [WORKTREES.md](../../WORKTREES.md) (max 3/repo; named branch `feat/<domain>-<action>`).
- Lane descriptor validated against [lanes/schema.json](../contracts/lanes/schema.json).

---

## Procedure (8 steps)

### 1. Preflight

Confirm the disposition row is actionable and the lane is isolated.

| Check | Command / action |
|-------|------------------|
| Row FSM | `disposition-index.json` → `fsm_state: ready` |
| Chokepoints | `chokepoints.json` — no blocking dependents for this source |
| Overlap | Morph router / file-overlap serializer — no concurrent `owns` collision |
| Harness | Lane descriptor `harness` + `harness_compat` set; AACP bundle version pinned |

If any check fails → set FSM to **`blocked`**, document reason in session evidence, exit lane.

### 2. Target workspace prep

Prepare the **destination** repo before moving code out of HexaKit.

1. Create or attach worktree: `<TargetRepo>-wtrees/<wave>-<lane>`.
2. Branch: `feat/<domain>-<crate>-relocate` (match lane descriptor).
3. Add/update `BOUNDARY.md` — declare new crate paths and forbidden cross-domain imports.
4. Ensure CI skeleton exists (`.github/workflows/ci.yml`, `cargo test --workspace` baseline).

### 3. Move

Transfer source tree from HexaKit to target. Choose strategy by disposition row:

| Strategy | When | Notes |
|----------|------|-------|
| **Subtree split** | Default for crates with clean history | `git subtree split` or filtered export |
| **Copy + history** | Large tangled history | Copy tree; preserve commit refs in `docs/history/` |
| **Copy only** | Assessment-only repos (e.g. focalpoint) | No history rewrite; document provenance |

Record source paths in lane descriptor `owns`. Do **not** delete HexaKit source yet — stub comes in step 6.

### 4. Manifest surgery

Update build manifests on **both** sides.

**Target repo:**

- Add crate to workspace `Cargo.toml` members (or equivalent manifest).
- Wire path dependencies to domain crates post-relocation.
- Run `cargo check --workspace`.

**HexaKit (source):**

- Remove crate from workspace members (or mark `[workspace]` exclude).
- Drop path deps that pointed at relocated crate.
- Ensure remaining workspace still builds (`cargo check --workspace`).

For Python/TS edges, mirror the same pattern in `pyproject.toml`, `package.json`, or phenoSDK manifest stubs.

### 5. Repoint dependents

Org-wide dependency repoint is the highest-risk step. Batch dependent PRs when chokepoints fan out.

1. Search: `gh api search/code?q=<crate_name>+org:<REDACTED>`
2. For each dependent repo in chokepoint matrix, open a repoint PR:
   - Replace HexaKit path/git dep with canonical domain repo + version pin.
3. Merge dependent PRs **before** or **in parallel with** target merge (never leave dangling path deps).
4. Update `registry/chokepoints.json` when a dependent is cleared.

### 6. Stub source path

Leave a pointer in HexaKit so agents and CI do not rediscover deleted paths.

Create `MIGRATED.md` in the former source directory (see [python/pheno-types/MIGRATED.md](../../python/pheno-types/MIGRATED.md) as template):

- Disposition row ID
- Canonical repo URL
- Migration date
- Consumer redirect instructions
- Maintainer note: remove stub when downstream refs are cleared

Optionally retain a minimal README redirect; remove implementation, tests, and workspace membership.

### 7. Verify

Run lane descriptor `verify` commands plus ecosystem gates:

```bash
# Target repo (from lane descriptor verify[])
cargo test -p <crate>
cargo test --workspace

# HexaKit
cargo check --workspace
cargo test --workspace   # if applicable

# Fleet
bun run tools/check-ecosystem.ts --map-only
hexakit boundary lint     # when available
```

All commands must pass before opening merge PR. Capture output in session `EVIDENCE.md`.

### 8. Index and pin

Close the lane and update fleet SSOT.

1. Merge target PR + HexaKit stub PR.
2. Set disposition row FSM → **`done`** in `disposition-index.json`.
3. Bump `registry/components.lock` pin for the relocated component.
4. Run independent watcher / validate workflow if configured.
5. Confirm lane `exit_gate` predicates (PR merged, FSM done, watcher pass, FR tags).
6. Prune worktree within 48h per [WORKTREES.md](../../WORKTREES.md).

---

## Exit gate checklist

| Gate | Required |
|------|----------|
| Target PR merged | Yes |
| HexaKit stub PR merged | Yes |
| FSM `done` | Yes |
| `components.lock` updated | Yes |
| `check-ecosystem.ts` green | Yes |
| Session evidence filed | Yes |

---

## Lane class reference

| Class | Worktree | Harness | Lock |
|-------|----------|---------|------|
| MUTATE_RELOCATE | Required | forge / cursor-agent | 1/repo + global cargo |
| MUTATE_SCAFFOLD | Single branch | any | 1/repo |
| READ_AUDIT | Optional | forge 18-wide | none |
| LONG_VERIFY | worktree | thegent `--owner` | session |

See [Harness API](../contracts/harness-api.md) for adapter dispatch and lane descriptor fields.

---

## Related artifacts

- [DISPOSITION.md](../boundary/DISPOSITION.md) — authoritative module table
- [FLEET_INIT.md](../scaffolding/FLEET_INIT.md) — scaffolding-only end-state
- [Harness API](../contracts/harness-api.md) — lane dispatch contract
- [Lane descriptor schema](../contracts/lanes/schema.json) — machine-readable lane format
