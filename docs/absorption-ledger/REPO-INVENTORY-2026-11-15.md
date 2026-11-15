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
| `absorb-or-keep` | 6 | history preserved, content not absorbed anywhere |
| `preserve-first` | 7 | no preserved refs at all |
| `delete-eligible` | 2 | history and content both present |
| **total** | **111** | |

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

## `preserve-first` (7): no preserved refs

New repositories that appeared after the last sweep, or were never covered:

| Repository | MB | Note |
|---|---:|---|
| `argis-extensions-preserved-20261114` | 9.2 | appeared 2026-11-14, name suggests a preservation copy |
| `claude-plugins-official` | 19.1 | public |
| `cliproxyapi-plusplus` | 7.7 | private |
| `hexakit` | 12.7 | private |
| `hwledger` | 0.6 | private |
| `slipstream` | 32.2 | public |
| `.github` | 0.1 | org config; git forbids a ref component starting with a dot, so it cannot be preserved under its own name |

These are all cheap to preserve and should be, whatever the target turns out to be.

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

## `absorb-or-keep` (6)

`HarnessDesk`, `StealthStartup`, `chatta`, `phenoreg-browser-audit`,
`zz-ref-HeliosCLI`, `zz-ref-HeliosLite`. History is preserved (80, 1, 174, 13,
1,340 and 1,064 refs). None has an absorbed content tree, so absorbing is the work
that remains before any deletion.

## What this inventory does not claim

- That `refs > 0` means the history is complete. It means the ref set matched the
  source when preserved; live repositories drift afterwards.
- That a missing local tree means the content is gone. BytePort demonstrated the
  opposite: its files are split across `absorption/byteport` and
  `_archived/byteport`, and checking only one produced 321 false "missing" files.
  Content presence here is a name-based check and needs the union-coverage check
  before any deletion.
- That the count is stable. It has gone 86, 104, 110, 111 in one day.
