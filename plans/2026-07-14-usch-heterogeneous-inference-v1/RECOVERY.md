# Repository recovery and integration boundary

Snapshot date: 2026-07-14

## Completed external change

The private GitHub repository `KooshaPari/pheno-harness` was verified archived,
then unarchived by changing only the repository `archived` metadata field. A
read-back confirmed `archived: false`. No branch, commit, issue, permission,
local file, or worktree state was changed as part of the unarchive operation.

## Most recent recorded graph audit

Read-only GitHub audit observed at `2026-07-15T04:23:37Z`:

```text
63aa0be  common baseline and local shallow boundary
├─ local-only:  d30e94a -> e069e24 + dirty/untracked worktree
└─ remote-only: 18 commits -> 43a7ca4
```

Recorded snapshot, not a live invariant:

| Item | Value |
|---|---|
| Checkout | `C:\Users\koosh\pheno-harness` |
| Observed remote `main` | `43a7ca4215b14f7e09321d24dbb0a73d4af2689f` (repository `pushed_at` 2026-07-15T04:16:55Z) |
| Local `HEAD` | `e069e24c8ee7bbd0feaba79bbada24078239f04c` |
| Common boundary | `63aa0bebff442ea06c31d6bcac6ffe6dc4467e57` |
| Local-only commits | `d30e94a`, `e069e24` |
| Remote-only commits | 18 after the common boundary |
| Observed branches | `main`, `feat/qwen-host-engine`, `feat/qwen-metal-kernels` |
| Submodule | `agileplus-specs` uninitialized at `13fcdc554c73abc765a34592a244abcf16eddf43` |

The cached local `origin/main` still points at the common boundary, so the
ordinary `ahead 2` display is misleading relative to live GitHub. GitHub does
not know the two local-only commits.

The read-only local sample at `2026-07-15T04:24:10Z` had 19 modified tracked
files, zero staged or unmerged files, 270 untracked paths, and 1,135 ignored
files. Counts moved during the wider audit, so the checkout was not quiescent. The
repository is shallow; `git fsck` found no corruption but reported seven
dangling blobs (about 130 KiB) that a refs-only bundle would omit. Counts are
observations, not invariants; any resumed writer invalidates the sample.

## Latest historical preservation anchor

The latest verified recovery anchor is
`C:\Users\koosh\pheno-harness-preserve\20260715T200754Z`, as recorded in the
external `CHECKPOINTS.md`. Its `SHA256SUMS.txt` SHA-256 is
`1dd7a8bc0fd074b49af730607f1b4b93f20933e82ea7491b5ff2de2657aa11c3` and its
archive SHA-256 is
`598f0dde3e9ab86e69e7a9ef9bd7811978eccba1bf4c26616189715d3296897c`.
It contains 1,982 byte-hashed files and matched its source inventory and Git
status before and after capture. It is historical, not a current-final-state
capture: `C:\Users\koosh\pheno-harness-preserve\CHECKPOINTS.md` records later
deltas and remains the authoritative local preservation chronology.

## Original historical preservation anchor

The earlier source checkout was preserved locally at
`C:\Users\koosh\pheno-harness-preserve\20260715T015932Z` before any graph
reconciliation. The regular-file archive is 1,527,684 bytes with SHA-256
`45702867deff193305f49ae059b520bdcf67eb7375e3b1d1891cc5c56af20bc7`.
The packet's `SHA256SUMS.txt` trust anchor, computed independently of the
manifest entries, is
`f96ee244498b5e912900adef4f6530864bd053ebd6d0cc3cbf76061453004969`.
Supply that value through `--packet-checksum-manifest-sha256`; keep an
operator-controlled copy outside the packet because a digest stored only beside
the files it authenticates is not an external trust anchor.
It contains 962 unique files totaling 10,245,000 bytes, including raw `.git`
objects and the seven dangling blobs. Independent verification found no
missing, extra, duplicate, size-mismatched, or hash-mismatched payloads.

The source-file manifest, reparse manifest, and Git status were byte-identical
before and after capture. The defense-in-depth local-only bundle has SHA-256
`7b04cd4abb47010ed50151e8eac9c5398457e816491b0a94a58541cd09f206fb`,
advertises `e069e24c8ee7bbd0feaba79bbada24078239f04c`, requires
`63aa0bebff442ea06c31d6bcac6ffe6dc4467e57`, and verifies successfully.

The tar is a verified regular-file snapshot, not a byte-for-byte NTFS image.
It intentionally excludes `bin/python`, `bin/python3`, `bin/python3.10`, and
`lib64`; their reparse metadata and exclusion reasons are recorded alongside
the archive. Empty directories, NTFS ACLs, alternate data streams, and exact
filesystem creation times are not preserved. The packet contains the private
repository's complete `.git` state plus ignored/untracked evidence and is not
secret-cleared: never publish, attach, or sync it to an untrusted system.

At the capture read-back, live GitHub `main` was still `29b9313` and the
repository remained private and unarchived. No remote mirror, submodule
recovery, clone/import, merge/cherry-pick, push/PR, or cleanup was performed.

## Post-capture delta

The verified packet remains intact but is now a historical snapshot, not
complete preservation of the current checkout. The earlier `03:41:35Z`
read-only comparison found 736 changed or new regular files relative to the
packet: four captured dirty tracked files changed, 23 captured untracked files
changed, four untracked files were new, 14 captured ignored files changed, and
691 ignored files were new. A later `04:25:55Z` sample observed 765 union delta
paths but three paths raced, so neither count is an invariant or a replacement
for a fresh capture. Many ignored additions are generated test/cache material,
but they must be classified rather than silently assumed disposable.

`scripts/reconciliation_preflight.py` now provides a fail-closed, stdout-only
preflight using non-refreshing Git plumbing under `GIT_OPTIONAL_LOCKS=0`. It
reads checksum-covered packet files once through bounded regular-file handles
and reuses those verified bytes for manifest, inventory, tar, bundle, and HEAD
semantics. Bundle verification receives those exact bytes on stdin; Git reads
discard inherited `GIT_*` redirection and disable fsmonitor and hooks. It also
verifies the local graph, a separately digest-pinned bounded offline remote
snapshot, current content-hash deltas, Git control files, and two-sample
quiescence. `scripts/acquire_reconciliation_remote_snapshot.py` now produces
the consumer's exact remote-snapshot schema, but no compliant current artifact
has yet been persisted. The present checkout requires a fresh verified delta
capture after writers quiesce before disposable-clone reconciliation can be
reviewed.

### GET-only remote snapshot acquisition

The additive acquisition CLI makes only versioned GitHub REST `GET` requests
through `gh api`. It reads repository metadata, every bounded branch page, and
the exact default-branch ref twice; requires both observations to match; and
requires the compare endpoint to prove that the supplied common boundary is
the exact merge base of the observed live tip. The comparison deliberately
requests a non-first paginated page because GitHub omits its unrelated
changed-file payload after page one while retaining the graph summary. GitHub
documents the relevant
[branch pagination](https://docs.github.com/en/rest/branches/branches),
[repository metadata](https://docs.github.com/en/rest/repos/repos), and
[commit comparison](https://docs.github.com/en/rest/commits/commits)
contracts. The CLI selects API version `2026-03-10` explicitly.

It has no output-file, token, mutation, or Git option. On success it emits
exactly one canonical, LF-terminated
`pheno.reconciliation.remote-snapshot.v1` document on stdout. It captures and
never relays raw `gh` stderr. A failure emits the distinct
`pheno.reconciliation.remote-snapshot-error.v1` schema and exits 2; never pin
or feed an error document to the preflight.

After remote pushers are paused, an operator may capture the bytes outside the
source checkout and independently pin them:

```powershell
python scripts/acquire_reconciliation_remote_snapshot.py `
  --repository KooshaPari/pheno-harness `
  --expected-default-branch main `
  --base-sha 63aa0bebff442ea06c31d6bcac6ffe6dc4467e57 `
  --local-sha e069e24c8ee7bbd0feaba79bbada24078239f04c `
  > C:\operator-controlled\pheno-remote-snapshot.cjson
$remoteSnapshotSha256 = (Get-FileHash -Algorithm SHA256 `
  C:\operator-controlled\pheno-remote-snapshot.cjson).Hash.ToLower()
```

The `local_sha` is an explicit operator pin carried for the offline preflight;
the acquisition CLI does not imply that GitHub knows the local-only commit.
`--expected-live-sha` can pin a prior observation. Repeated
`--expected-branch NAME=SHA` options form an exact whole-set guard, not a
partial allowlist, and must include the default branch. The resulting digest
authenticates the exact captured bytes but not the GitHub account or operator;
retain it in a separate operator-controlled record. The snapshot describes its
acquisition window only, so it does not remove the remote-writer quiescence
gate.

## Hard safety rule

Until recovery is complete, do **not** run any of the following in the current
checkout:

- `git pull`, merge, or rebase;
- reset, checkout/switch with overwrite, restore, or clean;
- force operations or an in-place history rewrite;
- a push that assumes cached `origin/main` is current;
- submodule initialization that can overwrite or introduce a second moving
  state before the main tree is reconciled.

A Git bundle alone is insufficient: the repository is shallow, and much of the
valuable state is modified, ignored, or untracked rather than committed.

## No-loss recovery sequence

1. Quiesce all writers and record process/agent ownership.
2. **Original snapshot completed; fresh delta still required:** after writers
   stop, create a verified sibling delta capture including current `.git`,
   ignored files, and untracked files, with explicit reparse exclusions and
   hashes; keep the source checkout untouched during capture.
3. Clone the current GitHub repository into a new sibling directory and retain
   the exact branch set from a fresh digest-pinned remote snapshot (three at
   the recorded audit; do not assume that count remains current).
4. Import the original checkout's local `main` as a named recovery branch in
   the new clone without moving remote `main`.
5. Reconcile the two local-only commits against the exact remote range from
   that snapshot (18 commits at the recorded audit) in the new clone with an
   explicit three-way review.
6. Export the original tracked worktree diff separately and review/apply it.
7. Copy reviewed untracked/ignored content using the manifest, rather than a
   blanket overwrite.
8. Initialize or recover `agileplus-specs` only after the parent integration is
   stable.
9. Run repository tests and compare manifests before decommissioning the
   original checkout.

A successful reconciliation preflight is only readiness for disposable-clone
review. Its self-hashed policy explicitly forbids Git mutation and
reconciliation authorization and records `reconciliation_performed: false`
with `completion_status: NOT_PERFORMED`. Verified preservation packets, a
digest-pinned remote snapshot, and an exact branch set therefore cannot be
presented as evidence that reconciliation was authorized or completed.

Only the local preservation portion of this sequence has been performed. The
remaining mirror, import, reconciliation, publication, and decommission steps
need explicit authorization after both local writers and remote pushers are
paused.

## Related recovery evidence

- `C:\Users\koosh\repos\phenotype-tooling\docs\absorbed-from-pheno-harness\ABSORPTION.md`
  records that an earlier repository incarnation was archived/deleted on
  2026-06-21 but contains no source backup.
- `C:\Users\koosh\_pheno_absorb` contains notes, not a repository backup.
- `C:\Users\koosh\_arch_pheno-harness.json` is an old API snapshot and contains
  a plaintext temporary-token-like field. Never publish or quote it; rotate or
  revoke the credential after preservation if its validity is uncertain.
- Targeted scans found no credible `pheno-harness`/USCH archive in the project,
  temp, Desktop, Documents, Downloads, OneDrive, or repository roots, and no
  `USCH` string in the checkout. This is broad targeted evidence, not a claim
  that every byte of every volume was exhaustively scanned.

The directory created for this research packet is intentionally new and unique.
It does not resolve the divergence and must be included in the recovery
manifest like every other untracked path.
