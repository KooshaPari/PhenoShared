# Deletion Record — where absorbed repositories went

Every repository listed here has been deleted from GitHub. This file exists so
that "it was absorbed" is checkable rather than asserted: for each entry, the
surviving location of its files, its history and its discussion is named.

**Scope.** This covers the 2026-11-12 waves only. Earlier waves are recorded in
[`../ABSORPTION_INDEX.md`](../ABSORPTION_INDEX.md), which remains the canonical
index of absorbed and retired repositories; read the two together. This file
exists because those waves introduced preservation methods that the index does
not describe, and because the proof for each one needs to be readable beside the
deletion rather than inferred from a worklog reference.

Nothing may be added here before the corresponding proof exists. The checks are
in `scripts/`:

| Check | Script | What it proves |
|---|---|---|
| Code absorption | `verify_absorption.py` | Every source file exists in `absorption/`, path for path |
| Private data absorption | `absorb_private.py` | Every file is byte-identical, by comparing git blob ids |
| History | `prepare_deletion.py` | A bundle, or refs under `refs/preserved/`, round-trips |
| Discussion | `prepare_deletion.py` | Issues, PRs and comments exported to the registry |
| Local fork changes | `export_fork_patches.py` | The combined diff applies to the base and reproduces the fork tree |

## 2026-11-12 — private ops repositories

Nine small private operations repositories were absorbed into the private
registry, not into PhenoShared, because they hold configuration and data rather
than code destined for the public tree.

Each was written to `PhenoRegistry/repos/<repo>/tree/` and its full history to
`refs/preserved/<repo>/`. The proof is a comparison of git blob ids between the
source tree and the pushed tree: git object ids are content hashes, so equality
per path means every file arrived byte for byte. 769 files were compared across
the nine and all matched. The registry was then read back independently and
each tree and ref namespace confirmed present.

| Repository | Files | Commits | Refs |
|---|---:|---:|---:|
| `agentapi` | 1 | 8 | 2 |
| `runner-smoke` | 3 | 8 | 3 |
| `nexus` | 22 | 16 | 8 |
| `tailnet-smb-setup` | 21 | 20 | 1 |
| `harness-ops` | 69 | 55 | 2 |
| `PhenoMCP` | 1 | 112 | 2 |
| `host-credentials` | 5 | 1 | 1 |
| `host-ops` | 683 | 894 | 85 |
| `PhenoMCPServers` | 473 | 115 | 3 |

`host-ops` was originally recorded here as 174 files, 204 commits and 5 refs.
Those were the numbers at the moment of the first pass, and they stopped being
the truth almost immediately: the repository was re-created at
2026-11-12T11:17:10Z, minutes after this wave, and work continued in it. The
figure above is the 2026-11-14 refresh, when the whole default branch was
grafted (`repos/host-ops/tree/`, 683 files, blob-identical) and every ref
re-pushed to `refs/preserved/host-ops/`, at source `f8b39eb8`.
**`host-ops` is live as of that date, so
its deletion is outstanding rather than done**, and the flat 107-file copy from
the 2026-11-11 per-file split was removed at the same time as a superseded
duplicate.

`host-credentials` held live credentials. Moving it into the private registry
and deleting the repository reduces exposure: the material is now in one
private place instead of two.

## 2026-11-12 — histories too large for a bundle

| Repository | History | Preserved as |
|---|---|---|
| `PhenoMLX-temp` | 187 MB, 421 commits, 8179 objects | `refs/preserved/PhenoMLX-temp/` in the registry |
| `phenotype-canonicalization` | 116 KB bundle | `repos/phenotype-canonicalization/history/` |

`PhenoMLX-temp` could not be stored as a bundle at all: GitHub rejects any file
over 100 MB. Its objects were pushed as refs instead and verified by fetching
them back (same tip `70529a8`, same 421 commits, same 8179 objects) and running
`git fsck --full`.

## 2026-11-12 — dependency forks

Eleven `zz-*` forks carried local work on top of third-party projects. Their
`ahead_by` counts were not the whole story: the earlier authorship check showed
4 to 242 commits authored here in each, so none were mere dependency pins.

These were initially going to be exported as patch series. That failed for a
good reason: several forks have an inherited default branch that is identical
to upstream while the real work sits on another branch. `zz-aa-dep-UnityDoorstop`
is the clear case, with `master` matching upstream and the work on `main`. Any
"diff the default branch" approach either exports nothing or exports the wrong
branch, and choosing the branch by guesswork is not acceptable.

So every ref was preserved instead, under `refs/preserved/<repo>/` in the
registry. Identity is the proof: each ref name and tip sha was read back from
the registry and compared against the source, so the check cannot pass while
anything is missing, and no branch had to be interpreted.

| Repository | Refs preserved | Commits |
|---|---:|---:|
| `zz-aa-dep-CompoundSpheres3D` | 5 | 134 |
| `zz-aa-dep-UnityDoorstop` | 65 | 433 |
| `zz-aa-dep-MobileCli` | 118 | 470 |
| `zz-aa-dep-TurboQuant` | 17 | 385 |
| `zz-pause-ref-Synthia` | 12 | 1,186 |
| `zz-aa-dep-AgentApiPlusPlus` | 24 | 934 |
| `zz-aa-dep-PhenoUnslothStudio` | 2 | 6,917 |
| `zz-aa-dep-AirLock` | 94 | 958 |
| `zz-aa-dep-CliproxyApiPlusPlus` | 832 | 8,835 |
| `zz-aa-dep-Bifrost` | 1,664 | 7,169 |
| `zz-aa-dep-Planify` | 117 | 9,153 |

2,950 refs in total. The ref counts are the reason this approach was taken
rather than a single diff: `CliproxyApiPlusPlus` has 832 branches and `Bifrost`
1,664. Any single-branch export would have discarded almost all of it.

Before deleting, a search for `zz-aa-dep` across PhenoShared and the local
Phenotype tree found no references, so no build resolves these forks as a
dependency.

## 2026-11-12 — gaps that cannot be closed

Nine repositories were deleted in an earlier pass with their files verified but
without a history bundle or a discussion export: `Authvault`, `SessionLedger`,
`ResearchLedger`, `cvp-fixture`, `netweave-3`, `phenotype-router-spec`,
`herdr-session-adapter`, `rule30-research`, `BytePort`.

Their files survive in `absorption/`. Their history and any issues or pull
requests did not, and cannot be reconstructed. Only a GitHub Support restore
within the retention window would recover them. `prepare_deletion.py` was
written so that this cannot happen again: it refuses to authorise a deletion
until history and discussion are both preserved.
