# Repository inventory and planned actions, 2026-11-16

Complete inventory: every live repository under `KooshaPari`, with the evidence
behind its classification and one action. The machine-readable form is
`REPO-INVENTORY-2026-11-15.csv` in this directory; regenerate with
`python scripts/inventory_all.py --csv`.

Columns: `repo`, `priv`, `mb`, `refs` (refs preserved in the registry),
`regtree` (a content tree exists at `PhenoRegistry/repos/<name>`), `local`
(absorbed or archived directories in PhenoShared), `category`, `action`.

## Action summary

| Action | Count | Meaning |
|---|---:|---|
| `keep` | 77 | deliberately retained; no action |
| `decide` | 19 | needs an owner decision, evidence already gathered |
| `absorb-or-keep` | 10 | history preserved, content confirmed nowhere in PhenoShared |
| `absorb-remainder` | 2 | content partly absorbed, remainder outstanding |
| `delete-eligible` | 3 | history and content both present |
| `preserve-first` | 1 | no preserved refs at all, and cannot have them |
| **total** | **112** | |

The count moved 111 -> 112 while this was being written: `phenotype-canonicalization`
appeared with no preserved refs. It is now preserved and sits in `delete-eligible`.

## The target question

The stated goal is two canonical homes. Of 112 repositories, **77 are `keep`**: 2
canonical homes, 25 recovery stores, 27 live products, 4 explicitly leave-alone,
15 archives and evidence, 4 destinations.

Two targets are in play and they need different work:

- **Target 2** means the 27 live products must be absorbed and deleted. The ledger
  recommends against it: it would dissolve their histories, issue trackers and
  release flows.
- **Target ~35** means the live products stay as products, and consolidation is
  finished once the `decide`, `absorb-*` and `delete-eligible` rows settle.

Until one is chosen, the 77 `keep` rows are a recommendation, not a path to 2.

## Content search: what the 12 `absorb-or-keep` actually turned out to be

The previous inventory classified these by **name** against three conventional
locations. BytePort had already shown that check to be wrong (its files are split
across `absorption/byteport` and `_archived/byteport`), so the whole PhenoShared
tree was searched for any directory whose normalised name matches, at depth four,
and every candidate was measured by git blob id.

Two were found under names the lookup could not have guessed:

| Repository | Found at | Repo files | Identical | Different | Repo-only |
|---|---|---:|---:|---:|---:|
| `hwledger` | `crates/hwledger` | 404 | 192 | 102 | 110 |
| `hexakit` | `crates/hexa-kit` | 3,794 | 2,740 | 489 | 565 |

Both are **partially** absorbed: a substantial body of the repository's files is
absent from the PhenoShared crate, so neither can be called absorbed.

The other ten have no matching directory anywhere in the tree and are classified
`content confirmed nowhere in PhenoShared`:

`argis-extensions-preserved-20261114` (1,628 files), `claude-plugins-official`
(765), `cliproxyapi-plusplus` (3,129), `slipstream` (2,061), `HarnessDesk` (249),
`StealthStartup` (34), `chatta` (4,521), `phenoreg-browser-audit` (367),
`zz-ref-HeliosCLI` (6,387), `zz-ref-HeliosLite` (1,560).

For these, history exists in the registry and content exists only in the live
repository. Deleting any of them would lose the files.

## `preserve-first` (1)

Only `.github` remains, and it cannot be fixed under its current name: git forbids
a ref component starting with a dot, so `refs/preserved/.github/` is not a legal
ref. It would need a renamed namespace such as `refs/preserved/github-org/`.

## `delete-eligible` (3)

| Repository | MB | Refs | Content |
|---|---:|---:|---|
| `host-credentials` | 1.0 | 1 | registry tree |
| `host-ops` | 6.6 | 113 | registry tree |
| `phenotype-canonicalization` | 0.1 | 1 | registry tree |

All three have history preserved and a content tree in the registry. `host-ops`
has been restored by the operator once already and both `host-credentials` and
`host-ops` were recreated during the 2026-11-14 burst, so deleting them may simply
be undone by whatever did that.

## `decide` (19)

Nine `audit-snapshot-*` imports and ten repositories recreated on 2026-11-14
(`BytePort`, `Personal`, `PhenoVCS`, `audit-system`, `cvp-fixture`, `dagrun`,
`harness-ops`, `phenotype-landing`, `rule30-research`, `zz-aa-dep-AirLock`).

Eight of the snapshots are preserved and their content is unique against their
live counterparts. For `OmniRoute` the live versions were shown to be newer, so
the snapshots are older states. This row is a judgement call about whether near-
duplicate snapshots should exist at all, not an evidence gap.

## What this inventory does not claim

- That `refs > 0` means history is complete. It matched at preservation time;
  live repositories drift afterwards.
- That a repository absent from the tree is absent from the registry's preserved
  blobs. Search-indexed trees were checked; the registry's `repos/` trees were
  checked by name only.
- That the count is stable. It has gone 86, 104, 110, 111, 112 in two days.
