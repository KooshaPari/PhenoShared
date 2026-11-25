# Airlock SQUASH POLICY — 2026-07-29 Sponsor Directive

**Status:** STANDING RULE — supersedes any prior squash guidance in any docket under `AgilePlus/docs/airlock/`.

---

## The Rule (verbatim, decoded from sponsor)

> *"NEVER squash parent repos with deep important histories. only a consumed repo AND ONLY AS A NEW MAIN BRANCH WHILE YOU KEEP ONE FULL HISTORY OR OTHER FULL HISTORY BRANCHES PRESENT"*

## Decoded Policy

1. **NEVER squash a parent repo.**
   - A "parent repo" is one that is a canonical fork of an external upstream (e.g., `phenotype-omlx` ← `jundot/omlx`; `forgecode` ← `antinomyhq/forgecode`; `substrate` ← its own origin; `AgilePlus` ← itself as the working CLI; `cliproxyapi-plusplus` ← `router-for-me/CLIProxyAPI`).
   - "Deep important history" = branches with novel commits not in `main`, OR any repo that is the canonical home for its work.

2. **A consumed repo MAY be squashed.**
   - "Consumed" = a repo whose work has been migrated/absorbed into another canonical repo and now exists solely as a redundant copy (e.g., `thegent-sharecli` if fully absorbed into `thegent`; `pheno-forge-smoke` after import to `forgecode`).
   - Consumption must be **provable** (verified by diff/cherry-pick evidence), not assumed.

3. **Squash destination: a NEW MAIN BRANCH, not the existing `main`.**
   - The existing `main` keeps its full history.
   - The squashed commit lives on a new branch (e.g., `main-squashed-2026-07-29`).

4. **Full-history preservation is mandatory.**
   - At least one full-history branch (or multiple full-history branches) must remain present in the repo after any squash.
   - Forks retain their default branch as the full-history reference.
   - Repos with archived branches (e.g., `zz-archive-*`) retain those branches as receipts.

5. **Deletion of any repo is permanently forbidden** regardless of policy compliance.

---

## Application Per Repo Group

| Group | Repo | Parent? | Consumed? | Squash Allowed? |
|---|---|---|---|---|
| G1 | `thegent` | **YES** (canonical CLI) | no | ❌ never |
| G1 | `thegent-workspace` | no (pointer) | yes (after redirect) | ✅ only as new branch with full history kept |
| G1 | `thegent-sharecli` | no (sub-product) | needs verification | ✅ only as new branch if fully absorbed |
| G1 | `zz-archive-thegent-dispatch` | n/a | n/a | ❌ never (archive receipt) |
| G2 | `vibeproxy-monitoring-unified` | **YES** | no | ❌ never |
| G2 | `vibeproxy` | n/a | already 404 | n/a |
| G3 | `phenotype-omlx` | **YES** (fork of `jundot/omlx`) | no | ❌ never — but **NEW branch** allowed for re-fork synthesis |
| G4 | `forgecode` | **YES** (fork of `antinomyhq/forgecode`) | no | ❌ never |
| G4 | `pheno-forge-smoke` | no | yes (after import to forgecode) | ✅ only as new branch |
| G4 | `pheno-forge-plugins` | no | yes (after import to forgecode) | ✅ only as new branch |
| G4 | `phenoForge` | no (distinct project) | no | ❌ never |
| G4 | `MCPForge` | **YES** (fork of `isaacphi/mcp-language-server`) | no | ❌ never |
| G5 | `substrate` | **YES** | no | ❌ never |
| G5 | `substrate-adapters-bundle` | no (meta-repo) | no (but is a meta-bundle of sub-crates) | ❌ never |
| G6 | `AgilePlus` | **YES** | no | ❌ never |
| G7 | `agentapi-plusplus` | **YES** (fork of `coder/agentapi`) | no | ❌ never |
| G7 | `cliproxyapi-plusplus` | **YES** (fork of `router-for-me/CLIProxyAPI`) | no | ❌ never |
| G7 | `context-mode-plusplus` | **YES** (upstream-fork) | no | ❌ never |
| G7 | `PlusForges` | no (meta-repo) | no | ❌ never (meta-pointer) |

---

## What "NEW MAIN BRANCH" Means in Practice

If a consumed repo is squashed:
- Local repo: `git checkout --orphan main-squashed-2026-07-29 && git commit -m "squashed: <description>"`. Original `main` is **untouched**.
- Push: `git push origin main-squashed-2026-07-29:main-squashed-2026-07-29` (new ref, not force-push).
- Default branch on GitHub: **NOT changed** (no UI action taken without explicit per-step ACK).
- Full-history branch: original `main` retained as the full-history reference.

If a fork's local HEAD is re-synthesized (e.g., G3A re-fork clean):
- Local: `git checkout -b upstream-sync-2026-07-29` off upstream `main`, then cherry-pick local-only commits.
- Push: `git push origin upstream-sync-2026-07-29` (new branch, not force-push).
- Default branch on GitHub: **NOT changed** unless explicitly ACK'd per step.

---

## Enforcement

- Every docket under `AgilePlus/docs/airlock/` that proposes a squash must reference this file and explicitly classify its target repo as `parent` or `consumed` per the table above.
- Dockets that propose squashing a `parent` repo are **superseded** and must be re-issued with a new-branch alternative.
- No `git push --force` to any branch on any repo.
- No `gh repo delete` on any repo.

---

**Adopted:** 2026-07-29 by sponsor directive (transcript context).
**Effective:** immediately.
**Supersedes:** any prior squash guidance in any `*.md` under `AgilePlus/docs/airlock/`.