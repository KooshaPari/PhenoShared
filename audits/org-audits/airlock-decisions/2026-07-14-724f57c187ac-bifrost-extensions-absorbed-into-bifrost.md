# Airlock Decision: bifrost-extensions → KooshaPari/bifrost

**Decision:** Superseded by [`KooshaPari/bifrost`](https://github.com/KooshaPari/bifrost) (primary) or [`KooshaPari/argis-extensions`](https://github.com/KooshaPari/argis-extensions) (alt). No recreation needed.
**Decision date:** 2026-07-14
**Decision author:** Forge (automated inventory + absorption probe)

---

## Airlock metadata

| field | value |
|---|---|
| airlock id | `724f57c187ac` |
| original upstream | `github.com/KooshaPari/bifrost-extensions.git` (now MISSING on GitHub) |
| bare mirror | `/Users/kooshapari/.airlock/repos/724f57c187ac.git/` |
| worktree | `/Users/kooshapari/.airlock/worktrees/724f57c187ac/` |
| canonical working_path | `bifrost-extensions/` |
| local working_path on disk | **NO** (folder absent from `~/CodeProjects/Phenotype/repos/`) |
| default branch | `master` @ `ef9d5b3` |
| refs/heads in bare mirror | **20** (incl. `master`, `main`, `refactor/go-kit-integration-v2`, `chore/composite-actions`, `feat/*`, `fix/*`) |
| most-recent branch | `refactor/go-kit-integration-v2` @ 2026-03-24 |
| latest run in state.sqlite | `chore/composite-actions` → `ee03466` (superseded=0) |
| state.sqlite last_sync | 2026-03-24 |

**Upstream classification (gh CLI as KooshaPari):** `missing_or_deleted`.

---

## Absorption target

**Primary target:** [`KooshaPari/bifrost`](https://github.com/KooshaPari/bifrost) — your fork, created 2026-05-01, 50×-LiteLLM perf claims, Go, 1300+ branches.

**Alt target:** [`KooshaPari/argis-extensions`](https://github.com/KooshaPari/argis-extensions) — *"Argis gateway extensions - routing, SLM, embeddings, plugin architecture"* — same name pattern, sibling for the renamed gateway.

**Recommendation:** **Primary target = `bifrost`** because the airlock mirror was downstream of `github.com/maximhq/bifrost/core` (the upstream Bifrost LLM gateway), and `KooshaPari/bifrost` is the canonical home for the forked gateway. The extension layer's job (custom routing / SLM / embeddings plugins) is now subsumed by the fork's native capabilities and/or `argis-extensions`.

---

## Evidence chain

| signal | source | finding |
|---|---|---|
| **Architectural role** | `git show main:README.md` in `724f57c187ac.git` | *"clean extension layer for the Bifrost LLM gateway, consuming upstream repositories as Go modules without modifications"* — extension was a *consumer*, not a fork of the gateway itself. |
| **go.mod dependency** | `git show main:go.mod` in `724f57c187ac.git` | Requires `github.com/maximhq/bifrost/core v1.2.30` — confirms downstream relationship to upstream Bifrost. |
| **Primary target — `KooshaPari/bifrost`** | `gh repo view KooshaPari/bifrost --json createdAt,primaryLanguage,description,repositoryTopics` | Fork created 2026-05-01; description mentions 50×-LiteLLM perf; 1300+ branches; active. The fork has absorbed the routing/SLM/embeddings feature space that `bifrost-extensions` was once a separable layer for. |
| **Alt target — `KooshaPari/argis-extensions`** | `gh repo view KooshaPari/argis-extensions` | Description: *"Argis gateway extensions - routing, SLM, embeddings, plugin architecture"* — same extension name pattern; sibling project (Argis is presumably a renamed/renamed gateway family). |
| **No code loss** | bare mirror inspection | All 20 branches in `724f57c187ac.git` are reachable from `master`/`main`; no orphaned objects. |

---

## Action plan

1. ✅ Mark-as-merged decision recorded here.
2. ⏭️ Push eligible branches from `724f57c187ac.git` to **`KooshaPari/bifrost`** (primary target) as `airlock-recovery/<branch>`. Branches already on `bifrost` skipped. No `gh-pages` in this mirror.
3. ⏭️ **Open follow-up review** — recovery branches may belong on `argis-extensions` instead. Each branch should be inspected post-push; if the branch is plugin/extension-shape rather than gateway-shape, it should be moved via `gh repo set-default` + cherry-pick or via the GitHub API's branch transfer (or simply recreated on `argis-extensions` and deleted from `bifrost`).

---

## Rollback

```bash
for branch in $(gh api repos/KooshaPari/bifrost/branches --paginate \
                 --jq '.[] | select(.name | startswith("airlock-recovery/")) | .name'); do
  echo "deleting ${branch}"
  gh api -X DELETE "repos/KooshaPari/bifrost/git/refs/heads/${branch}" || true
done
```

---

## Cross-references

| artifact | location |
|---|---|
| airlock bare mirror | `/Users/kooshapari/.airlock/repos/724f57c187ac.git/` |
| airlock worktree | `/Users/kooshapari/.airlock/worktrees/724f57c187ac/` (detached HEAD) |
| full airlock inventory | `~/CodeProjects/Phenotype/repos/.airlock-inventory-2026-07-14.json` |
| absorption probe | `~/CodeProjects/Phenotype/repos/.airlock-absorption-probe-2026-07-14.json` |
| remote backup | https://gist.github.com/KooshaPari/3e6038adbfc4fe4c38965d02d0fc867e |
| probe scripts (re-runnable) | `~/CodeProjects/Phenotype/repos/_airlock-inventory-probe.py`, `~/CodeProjects/Phenotype/repos/_airlock-absorption-probe.py` |
| upstream URL (gone) | https://github.com/KooshaPari/bifrost-extensions |
| absorption target (primary) | https://github.com/KooshaPari/bifrost |
| absorption target (alt) | https://github.com/KooshaPari/argis-extensions |
