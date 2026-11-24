# helioscope → helios-cli absorption assessment

**Status:** Blocked (do not subtree-merge full repo)  
**Plan reference:** `phenotype-registry/RATIONALIZATION_PLAN.md` — helioscope retires to helios-cli (canonical codex fork)  
**Date:** 2026-05-31

## Verdict

| Criterion                            | Result                                                                                                        |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| Same upstream (openai/codex)         | Yes — both are codex-monorepo forks                                                                           |
| Canonical absorber                   | **helios-cli** (`main`) — active Phenotype fork with CVE/workspace fixes                                      |
| Retire candidate                     | **helioscope** (`master`) — legacy fork; README still references `heliosCLI`                                  |
| `git merge-base`                     | **None** — unrelated histories after divergent rebases                                                        |
| Unique commits on helioscope         | ~283 (sample: harness version bumps, deny.toml, fleet docs)                                                   |
| Unique commits on helios-cli         | ~4169 ahead of helioscope tip                                                                                 |
| Full-tree `git subtree add --squash` | **Mechanically succeeds** but adds **~5,134 files** (~790k LOC) — duplicate codex monorepo, not consolidation |

## Why full subtree merge is rejected

1. **No merge-base** — cannot do a normal merge; only squash-subtree of entire tree.
2. **Duplicate payload** — subtree places a second full codex workspace under `vendor/` with no deduplication against existing `codex-rs/`.
3. **Plan intent** — Step 2 in `RATIONALIZATION_PLAN.md` lists helioscope retirement as **`gh repo archive` + husk README**, not code merge.
4. **helios-cli is strictly ahead** — Phenotype-specific security and workspace fixes (#522–#527) live on helios-cli only.

## Recommended path (reversible, PR-only)

1. **Archive** `KooshaPari/helioscope` with README redirect → `KooshaPari/helios-cli` (separate ops PR; not done in code-absorb PR).
2. **Cherry-pick audit** — if any of the ~283 helioscope-only commits contain unique fixes not on helios-cli, open targeted cherry-pick PRs (do not bulk subtree).
3. **Optional:** add `helioscope` to `phenotype-registry` redirect table when archive lands.

## Build verification (absorber)

Run on `helios-cli` `main` (or this branch) with target dir on `E:`:

```powershell
$env:CARGO_TARGET_DIR = 'E:\cargo-target\helios-cli'
cargo check --workspace --manifest-path codex-rs/Cargo.toml
```

CI on this repo (`rust-ci.yml`) is the authoritative green gate before any archive.

**Local check (2026-05-31, Windows):** `cargo check --workspace` in `codex-rs/` failed on pre-existing `codex-windows-sandbox` parse error (`setup_orchestrator.rs:838` unclosed delimiter) — not introduced by this assessment doc. Linux CI remains the merge gate.

## helioscope-only commit sample (for cherry-pick triage)

```
32e097e docs(fleet): branch protection audit report
028627f fix(pheno-cli): add missing README; fix(guardis): correct repo URL
0e0ae3d chore(helioscope): update harness crate versions
74be1c4 fix(helioscope): remove broken symlink CONSTITUTION.yaml
```

## Issue #596 triage (2026-06-18)

Issue #596 re-states the problem in different terms: the issue claims `helios-cli` is "10% SCAFFOLD … does not build" and asks the canonical repo to **migrate code in from helioscope/HeliosCLI** before archiving them. This assessment already concluded the opposite direction (archive helioscope; helios-cli is canonical), and the verdict is unchanged. The deltas are:

| #596 asks | Why it does not apply here |
| --- | --- |
| "Migrate the working CLI code from helioscope into helios-cli/" | Explicitly rejected above (line 17, "duplicate codex monorepo, not consolidation"). Cherry-pick only, never full subtree. |
| "Confirm helios-cli builds" | The current `main` is intentionally a governance/CI skeleton — `codex-rs/Cargo.toml` declares 78 workspace members whose crate sub-directories are not in this checkout, so `cargo check --workspace` will fail by design. A re-scope (decide whether helios-cli remains a codex fork or a thin wrapper) is the prerequisite, not a code migration. |
| "Archive helioscope and HeliosCLI" | Requires `gh repo archive` against `KooshaPari/*` — an org-admin operation that cannot be performed from inside this repo's working tree and is out of scope for a code PR. |
| "Update `phenotype-registry/ECOSYSTEM_MAP.md`" | Lives in a different repository (`KooshaPari/phenotype-registry`); the redirect-table edit is a separate PR in that repo. |

### Recommended in-repo follow-ups (for a follow-up issue, not #596's PR)

1. **Re-scope decision** — pick one of: (a) commit the missing `codex-rs/<member>/` source so the workspace builds, or (b) trim `codex-rs/Cargo.toml` to the members that actually have source and document the smaller scope. Without this, "Confirm helios-cli builds" is unachievable by editing code in this repo alone.
2. **Open the archive PRs in `phenotype-registry`** — add `helioscope` and `HeliosCLI` to that repo's redirect table pointing at `helios-cli`, then file the org-admin archive requests separately. Keep the redirect PR independent of any code change here.
3. **Cherry-pick triage** — when GitHub API access is available from CI, diff `helioscope` (283 unique commits) against `helios-cli` `main` and open targeted cherry-pick PRs for any net-new fixes. Do not bulk-subtree.
4. **Update this repo's README work-state header** only after the re-scope in (1) lands; the current "10% SCAFFOLD" header is accurate for the present state of the working tree and should not be softened without the build actually succeeding.
