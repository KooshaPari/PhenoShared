# Preservation sweep — completion and one data-loss bug it exposed

Date: 2026-11-14
Scope: every live repository under `KooshaPari`, reconciled against the ref
namespaces under `refs/preserved/` in `PhenoRegistry`.

## What the reconciliation found

`scripts/verify_all_preserved.py` compares each live repository's refs against
its preserved namespace, both read from the server with `git ls-remote`. At the
start of this pass the account held 86 live repositories:

| Group | Count | Disposition |
|---|---:|---|
| Already preserved and verified | 38 | done |
| Recovery stores | 25 | excluded by standing rule |
| Canonical homes (`PhenoShared`, `PhenoRegistry`) | 2 | never deleted |
| Outstanding | 21 | classified below |

Of the 21 outstanding, 16 were genuine preservation targets and are now
preserved. Five are deliberately not targets, and one cannot be:

| Repository | Refs | Decision |
|---|---:|---|
| `Civis` | 1482 | Live product, declined as an absorb target |
| `OmniRoute` | 1537 | Live product, declined as an absorb target |
| `cmux` | 7854 | Live product, "leave alone" |
| `Substrate` | 478 | "leave alone" |
| `Pine` | 120 | "leave alone" |
| `.github` | 8 | Org-level config, and git forbids a ref component starting with a dot |

Preserved in this pass, with the ref count and namespaces verified equal:

| Repository | Refs | Namespaces |
|---|---:|---|
| `zz-ref-HeliosLite` | 1064 | heads, keep, pull, sources, tags |
| `zz-pause-unk-Thegent` | 782 | heads, pull, tags |
| `Personal` | 263 | heads, pull |
| `zz-zz-agentcheck-zz-pause-Agentora` | 235 | heads, pull, sources |
| `zz-pause-inc-FocalPoint` | 214 | heads, pull, tags |
| `chatta` | 174 | heads, pull |
| `HarnessDesk` | 80 | heads, pull |
| `zz-zz-agentcheck-PhenoGfx` | 42 | heads, pull, tags |
| `phenoreg-browser-audit` | 13 | heads, pull |
| `argis-extensions` | 6 | heads |
| `zz-archive-agileplus-spec-harmonizer-tool` | 2 | heads, tags |
| `zz-archive-pheno-drift-detector` | 1 | heads |
| `zz-archive-pheno-predict` | 1 | heads |
| `zz-archive-source-drops-2026-07` | 1 | heads |
| `zz-zz-agentcheck-docs-5` | 1 | heads |
| `StealthStartup` | 1 | heads |

`zz-ref-HeliosLite` had only a 96 MB bundle from an earlier pass, capturing 1,061
refs; its current name carries 1,064. The bundle is a snapshot, not a live ref
namespace, so it could not be compared and could not be extended. Preserving the
refs directly is the fix.

## Two bugs in the verifier

### 1. A local fetch cannot verify a case-colliding ref set

`prepare_deletion.py` verified a push by fetching the preserved namespace back
into a scratch repository. On a case-insensitive filesystem that fails outright
when two refs differ only in case:

```
error: You're on a case-insensitive filesystem, and the remote you are
trying to fetch from has refs that differ only in case
```

`claude-remember` has exactly that pair, `refs/heads/release-preview-H1` and
`refs/heads/release-preview-h1`. The push was complete - all 184 refs, both
variants present - but the verification reported "1 missing" and refused to
authorise the deletion. The fault was in the checker, not the data.

The verifier now compares `git ls-remote` output from both sides. That reads the
server's refs directly, never materialises them as files, and cannot be fooled by
the filesystem's case handling.

### 2. Re-preserving deleted a live repository's captured branches

`preserve_refs.py` removed any registry ref the source no longer advertises,
reasoning that a leftover misrepresents the fork. That is right for an inherited
upstream branch. It is wrong for a branch the source deleted *after* the registry
captured it, because the registry copy is then the only remaining record.

Re-preserving `host-ops` hit this. 27 captured branches were removed, including
`fix/heavy-builds`, `fix/doctor-mold-check`, `fix/kcode-queue-and-clippy` and
`chore/d82-instrument`. Of those 27:

- 12 correspond to **merged** pull requests, so their content is in `main`;
- 2 correspond to **closed unmerged** pull requests, whose tips remain fetchable
  as `refs/pull/<n>/head`, which GitHub retains permanently;
- 5 have **no pull request at all**: `fix/closure-metrics-honesty`,
  `fix/d6.2-midflight-cancellations`, `fix/doctor-mold-check`,
  `fix/kcode-queue-and-clippy`, `chore/d82-instrument`.

Those five are the only real exposure, and the evidence says the work itself is
not lost. Searching `main`'s history for each topic finds a commit that covers it:

| Deleted branch | Matching commit on `main` |
|---|---|
| `fix/closure-metrics-honesty` | `5f87948` "make check-delegation-rule.sh honest and green" |
| `fix/d6.2-midflight-cancellations` | `abeb9eb` "tell a superseded cancellation from a dead one in D6.2" |
| `fix/doctor-mold-check` | `210cd0d` "doctor detects a runner image without mold (#14)" |
| `fix/kcode-queue-and-clippy` | `987e299` "D24.1 is a real clippy lint"; `533c52b` queue item overdue |
| `chore/d82-instrument` | `24ba199` "re-register the stale UNSOURCED line the instrument names" |

So the branch tips are gone from the registry, but the commits they held are
ancestors of `main` under different hashes. The exact tip commits cannot be
recovered by sha, because the sha was discarded with the ref; only GitHub Support
could restore one. No content is believed lost.

The tool now moves a stale ref to `refs/superseded/<repo>/` instead of deleting
it, creating the copy before removing the original so an interruption leaves a
duplicate rather than a gap. `scripts/recover_deleted_refs.py` scans the registry
for unreachable commits, which is the recovery path if this recurs.

**Lesson.** "Mirror the source exactly" is the wrong invariant for a live
repository. Preservation is append-only by nature; a check that requires equality
with a moving source will either fail constantly or force deletions. The check
should be that every source ref is present, not that nothing else is.

## Drift, not loss

Seven repositories failed the first sweep because they are under active
development and their refs moved after being preserved: `PhenoMLX` (a dependabot
branch renamed and PR 255 landed), `AgilePlus`, `KCode` (master advanced),
`KooshaPari` (playwright bumps), `PhenoApps`, `host-ops`, and `kimaki` (one branch
moved). Every difference is a new or moved ref; nothing was missing. Re-preserving
brings each snapshot current, and for a live repository a stale snapshot is
expected rather than a fault.
