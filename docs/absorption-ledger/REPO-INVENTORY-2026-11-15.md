# Repository inventory and planned actions, 2026-11-15

Complete inventory: every one of the 111 live repositories under `KooshaPari`,
with the evidence behind its classification and one action. The machine-readable
form is `REPO-INVENTORY-2026-11-15.csv` in this directory; regenerate it with
`python scripts/inventory_all.py --csv`.

Columns: `repo`, `priv`, `mb`, `refs` (refs preserved in the registry),
`regtree` (a content tree exists at `PhenoRegistry/repos/<name>`), `local`
(absorbed or archived directories in PhenoShared), `category`, `action`.

## Action summary

| Action | Count | Meaning |
|---|---:|---|
| `keep` | 77 | deliberately retained; no action |
| `decide` | 19 | needs an owner decision, evidence already gathered |
| `absorb-or-keep` | 12 | history preserved, content not absorbed anywhere |
| `delete-eligible` | 2 | history and content both present |
| `preserve-first` | 1 | no preserved refs at all |
| **total** | **111** | |

Six repositories moved out of `preserve-first` on 2026-11-15 when their refs were
preserved: `argis-extensions-preserved-20261114` (1 ref), `claude-plugins-official`
(2 refs, 4,830 commits), `cliproxyapi-plusplus` (1), `hexakit` (1), `hwledger` (1)
and `slipstream` (6 refs, 1,132 commits). They land in `absorb-or-keep` because
history now exists but no absorbed content was found for them by name.

## The target question

The stated goal is two canonical homes. The account has 111 repositories, and
**77 of them are classified `keep`**: 2 canonical homes, 25 recovery stores, 27
live products, 4 explicitly leave-alone, 15 archives and evidence, 4 destinations.

So two targets are actually in play and they need different work:

- **Target 2** (only `PhenoShared` and `PhenoRegistry` survive) means the 27 live
  products must be absorbed and deleted. The ledger recommends against that: it
  would dissolve their histories, issue trackers and release flows.
- **Target ~35** (2 canonical + 25 recovery + the 8 that must not be deleted)
  means the remaining live products stay as products, and consolidation is
  finished after the `decide` and `absorb-or-keep` rows are settled.

Until one is chosen, the 77 `keep` rows are a recommendation, not a plan to reach
2. This is the one question that gates everything else.

## `preserve-first` (1): no preserved refs

Only `.github` remains. It is org-level configuration, and it cannot be preserved
under its own name because git forbids a ref component starting with a dot, so
`refs/preserved/.github/` is not a legal ref. Preserving it would need a renamed
namespace such as `refs/preserved/github-org/`, which no current tooling does.

The six that were here on 2026-11-15 have been preserved and now sit in
`absorb-or-keep`:

| Repository | Refs | Commits |
|---|---:|---:|
| `argis-extensions-preserved-20261114` | 1 | 1 |
| `claude-plugins-official` | 2 | 4,830 |
| `cliproxyapi-plusplus` | 1 | 1 |
| `hexakit` | 1 | 1 |
| `hwledger` | 1 | 1 |
| `slipstream` | 6 | 1,132 |

## `delete-eligible` (2)

`host-credentials` (1.0 MB, 1 ref, registry tree present) and `host-ops`
(6.6 MB, 113 refs, registry tree present). Both have history preserved and content
absorbed. `host-ops` was restored by the operator once already, and both were
recreated during the 2026-11-14 burst, so deleting them may simply be undone.

## `decide` (19)

Nine `audit-snapshot-*` imports and ten repositories recreated on 2026-11-14
(`BytePort`, `Personal`, `PhenoVCS`, `audit-system`, `cvp-fixture`, `dagrun`,
`harness-ops`, `phenotype-landing`, `rule30-research`, `zz-aa-dep-AirLock`).

Eight of the snapshots are now preserved. Their content is unique against their
live counterparts, and for `OmniRoute` the live versions were shown to be newer,
so the snapshots are older states. This row is a judgement call about whether to
keep duplicate-ish snapshots at all, not an evidence gap.

## `absorb-or-keep` (12)

`HarnessDesk`, `StealthStartup`, `chatta`, `phenoreg-browser-audit`,
`zz-ref-HeliosCLI`, `zz-ref-HeliosLite`, plus the six preserved on 2026-11-15
(`argis-extensions-preserved-20261114`, `claude-plugins-official`,
`cliproxyapi-plusplus`, `hexakit`, `hwledger`, `slipstream`). History is preserved
for all twelve. None has an absorbed content tree found by name, so absorbing is
the work that remains before any deletion.

## What this inventory does not claim

- That `refs > 0` means the history is complete. It means the ref set matched the
  source when preserved; live repositories drift afterwards.
- That a missing local tree means the content is gone. BytePort demonstrated the
  opposite: its files are split across `absorption/byteport` and
  `_archived/byteport`, and checking only one produced 321 false "missing" files.
  Content presence here is a name-based check and needs the union-coverage check
  before any deletion.
- That the count is stable. It has gone 86, 104, 110, 111 in one day.
