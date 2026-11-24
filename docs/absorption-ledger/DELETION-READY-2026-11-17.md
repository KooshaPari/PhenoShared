# Deletion readiness, 2026-11-17

Three repositories now pass all three conditions, up from two, and the tool gap
that blocked private repositories is closed.

## `prepare_deletion.py` can now verify registry-absorbed content

`verify()` called `verify_absorption.py`, which compares a repository against
`absorption/<repo>/`. That directory only exists for content absorbed into the
public tree. Private and credential-bearing repositories are absorbed into the
registry at `repos/<repo>/tree/`, so they could never be authorised at all — a gap
in the tool, not in the data, and it blocked every private deletion.

`verify()` now picks the verifier from what exists on disk rather than from a
flag:

- `absorption/<repo>/` present → `verify_absorption.py`, as before
- otherwise → `verify_registry_tree()`, which walks root → `repos` → `<repo>` →
  `tree` and compares git blob ids path for path

The registry tree is reached by walking tree objects because a recursive listing
of an 8 GB registry times out.

## `absorb_private.py` could not run at all

It created its work directory under `~/CodeProjects/temp`, which does not exist,
so every invocation died with `FileNotFoundError` on `mkdtemp` before doing any
work. It now uses `KCODE_SCRATCH_DIR`, then `~/Agents/scratch`, then the system
temp — which also brings it in line with the workspace policy that scratch
belongs under the declared scratch root.

## Current state

| Repository | Content | History | Discussion | Status |
|---|---|---|---|---|
| `host-credentials` | 5/5 exact (registry tree) | bundle `a7e2155e24f9`, 1,064.6 KB | 0 issues, 0 pulls | **DELETE-AUTHORISED** |
| `host-ops` | 1173/1173 exact (registry tree) | bundle `05b8e4b6c877`, 8,730.1 KB | 300 issues, 298 pulls, 921 comments | **DELETE-AUTHORISED** |
| `phenotype-canonicalization` | 43/44 (absorption) | bundle `cdaa7cfe6994` + preserved ref | 0 issues, 0 pulls | deleted 2026-11-16, tombstoned |

### `host-ops` was the real repair

Before this pass its registry tree held 683 of 855 files. Its 172 absent files
were not incidental: `closure/evidence/*` is most of the closure programme's
record, including `d8.3-local-only-trees-20261114.md`, `offmachine-bundles.md`,
`preserved/phenovcs-fc1d2bf.patch` and the d227 and d5.1 entries.

Re-absorbing took it to 1173 files exact against a repository that has itself
grown to 1173 files, and for the first time exported its discussion — 1,519
threads that had never been captured. Deleting it before this pass would have
destroyed both the evidence and the discussion.

## What is still not true

- No deletion has run for `host-credentials` or `host-ops`. Both are authorised;
  authorisation is not execution.
- `phenotype-canonicalization` was deleted on 2026-11-16 and reappeared 68
  minutes later, so authorisation alone does not make a deletion durable while
  something replays `refs/preserved/`. It is tombstoned; whether the tombstone
  holds is the open question.
- Thread export for the snapshot and restored repos (the `decide` row) has not
  been run.
