# Restored and imported repositories, 2026-11-14

## What happened

Between 17:22 and 17:38 the account gained 18 repositories it had not had at the
start of the preservation sweep, taking the count from 86 to 104. Their
descriptions are machine-generated and fall into two families:

- `restored 2026-11-14: local only, ...` — six repositories
- `Snapshot import of <name> (2026-11-14): origin 404` — twelve repositories

Both families record the same thing: a deleted repository was recreated from a
local copy. Some of these are among the nine whose history `DELETIONS.md`
records as permanently unrecoverable.

## The "empty shells" were not empty

The API reports `size: 0` for all twelve of the snapshot imports. That field is
the disk usage of packed objects, not content, and every one of them turned out
to hold files. `scripts/prove_empty.py` walks every ref and lists every file
path, and it found no empty repository at all:

| Repository | Files |
|---|---:|
| `audit-snapshot-tooling` | 22,552 |
| `audit-snapshot-OmniRoute` | 13,989 |
| `audit-snapshot-pheno` | 8,876 |
| `audit-snapshot-HexaKit` | 3,308 |
| `audit-snapshot-AgilePlus` | 2,979 |
| `audit-snapshot-agentapi` | 2,605 |
| `audit-snapshot-argis` | 1,613 |
| `phenotype-landing` | 550 |
| `audit-snapshot-hwLedger` | 326 |
| `PhenoVCS` | 133 |
| `audit-snapshot-PhenoVCS` | 133 |
| `cvp-fixture` | 17 |

Nothing was deleted. A plan to remove them as empty would have destroyed between
17 files and 22,552 files per repository, and `size: 0` would have looked like
justification.

## Preserved in this pass

Eight of the eighteen were preserved, history verified ref-for-ref:

| Repository | Refs | Commits | Notes |
|---|---:|---:|---|
| `cvp-fixture` | 1 | 1 | single-commit snapshot |
| `rule30-research` | 2 | 13 | |
| `dagrun` | 1 | 53 | |
| `audit-system` | 2 | 43 | |
| `harness-ops` | 1 | 44 | 1 older ref quarantined |
| `phenotype-landing` | 1 | 1 | single-commit snapshot |
| `PhenoVCS` | 1 | 1 | single-commit snapshot |
| `zz-aa-dep-AirLock` | 211 | 1,017 | 93 original fork refs quarantined |

`zz-aa-dep-AirLock` is the interesting one. Its current 211 refs are upstream's,
not the fork's. All 93 of the fork's refs were moved to
`refs/superseded/zz-aa-dep-AirLock/` rather than deleted, so the fork is still
recoverable while the recreated repository matches the source.

The three repositories with one commit each are content recoveries, not history
recoveries. `DELETIONS.md` still describes their original history as lost; what
came back is a snapshot of the working tree.

`BytePort` was deliberately not touched. It was set aside for a separate look,
and it is 232 MB of restored content whose relationship to the deleted
repository's 680 files is not yet established.

## Deliberately not touched

`audit-snapshot-*`, `phenotype-landing` and `PhenoVCS` are snapshots whose
redundancy has not been checked. Each is a single ref of a repository that
already exists elsewhere under a live name, so the content is probably
duplicated — but "probably duplicated" is not the standard for deleting 22,552
files, and a tree comparison against the live counterpart has not been run.

## An environment fault worth recording

Partway through this pass, `bash` in the agent shell began resolving to
`C:\Windows\System32\bash.exe`, the WSL launcher, instead of Git Bash. The
symptom was confusing rather than obvious: `/c/Users/koosh/...` stopped
resolving, so `Agents/scratch` appeared to have been deleted, while `cmd /c dir`
showed it intact.

`where bash` explains it - the WSL stub precedes Git's bash on `PATH`. Shell
scripts must now be invoked through `"C:\Program Files\Git\usr\bin\bash.exe"`
explicitly. Anything read from a `/c/...` path in the last hour of this session
should be re-checked before it is trusted.
