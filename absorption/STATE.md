# Absorption ledger of record

This file is the ledger of record for the trees under `absorption/`. "Absorbed"
here means one specific thing: the tree has a disposition recorded elsewhere in
this repo (a row in `docs/ABSORPTION_INDEX.md`, a dossier under
`docs/absorbed-from/`, or a `PROVENANCE.md` naming the wave and source), and
that record states the content of the tree was copied in and how much of it
landed. It does not mean the tree is wired into the build, and it does not mean
the source repository still exists. Where the record is absent or does not
settle the question, the row says `UNKNOWN` or `PENDING` and names what would
settle it. Nothing below is a target, an estimate or a percentage; each cell is
a file that exists or a command that was run.

Rows are ordered as `ls -1a absorption/` plus the hidden entry `.team-status`,
which is 31 paths: 30 trees and this file. Every tree in that listing has
exactly one row.

| tree                               | kind | last touched | evidence                                                                                                                                                                       | state    |
| ---------------------------------- | ---- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| `.team-status`                     | dir  | 2026-11-11   | `PROVENANCE.md` present; `docs/ABSORPTION_INDEX.md` "Cleanup and backlog wave" row (7 files, NOTES_DOCS import)                                                                | ABSORBED |
| `analysis-archive`                 | dir  | 2026-11-11   | `PROVENANCE.md` present; index "Cleanup and backlog wave" row (tombstone, 2 files)                                                                                             | ABSORBED |
| `argisexec`                        | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-14 (4 default-branch files plus 2 branch-only)                                                                                              | ABSORBED |
| `Authvault`                        | dir  | 2026-11-11   | `PROVENANCE.md` present; index 2026-11-12 deletion row, 332/332; `Cargo.toml` and `package.json` present                                                                       | ABSORBED |
| `byteport`                         | dir  | 2026-11-11   | `PROVENANCE.md` present; index 2026-11-12 deletion row, 676/680, 3 files withheld to the private registry and 1 compiled binary excluded                                       | ABSORBED |
| `canvasApp`                        | dir  | 2026-11-11   | `PROVENANCE.md` present; index "Cleanup and backlog wave" row (205 files, vendored `.venv`/`node_modules` excluded)                                                            | ABSORBED |
| `cvp-fixture`                      | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-04, 17/17; `Cargo.toml` present                                                                                                             | ABSORBED |
| `helios-bench`                     | dir  | 2026-09-16   | no `PROVENANCE.md`; no `docs/ABSORPTION_INDEX.md` row; no `docs/absorbed-from/helios-bench/` dossier; not a root workspace member                                              | UNKNOWN  |
| `herdr-forgecode`                  | dir  | 2026-11-11   | `PROVENANCE.md` present; index "Cleanup and backlog wave" note, herdr plugins along with a history bundle in the private registry                                              | ABSORBED |
| `herdr-helioslite`                 | dir  | 2026-11-11   | `PROVENANCE.md` present; index "Cleanup and backlog wave" note, same plugin batch                                                                                              | ABSORBED |
| `herdr-jcode`                      | dir  | 2026-11-11   | `PROVENANCE.md` present; index "Cleanup and backlog wave" note, same plugin batch                                                                                              | ABSORBED |
| `herdr-session-adapter`            | dir  | 2026-11-10   | `PROVENANCE.md` present; index MRG-05, 12/12; `package.json` present                                                                                                           | ABSORBED |
| `kiro-adapters`                    | dir  | 2026-11-10   | `PROVENANCE.md` present; index MRG-06 (160 files, 1 withheld for a tailnet address); `pyproject.toml` present                                                                  | ABSORBED |
| `netweave-3`                       | dir  | 2026-11-12   | `PROVENANCE.md` present; index MRG-07, 30/30; `go.mod` present                                                                                                                 | ABSORBED |
| `pheno-forge`                      | dir  | 2026-09-17   | `PROVENANCE.md` present, but no `docs/ABSORPTION_INDEX.md` row and no `docs/absorbed-from/pheno-forge/` dossier                                                                | PENDING  |
| `phenoDesign-visual-production-v2` | dir  | 2026-09-27   | `PROVENANCE.md` present; index SPR-03; dossier `docs/absorbed-from/phenoDesign-visual-production-v2/README.md`                                                                 | ABSORBED |
| `PhenoInfra`                       | dir  | 2026-11-12   | `PROVENANCE.md` present; index SPR-05 plus a 265-commit bundle in the private registry; `Cargo.toml`, `package.json` and `pyproject.toml` present; not a root workspace member | ABSORBED |
| `PhenoMLX-temp`                    | dir  | 2026-11-12   | `PROVENANCE.md` present; index SPR-04, and the 2026-11-12 table records 1,059 of 5,736 paths with 303 real files short                                                         | PENDING  |
| `phenoStandards`                   | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-13 (25 files, 11 branches)                                                                                                                  | ABSORBED |
| `phenotype-canonicalization`       | dir  | 2026-09-27   | `PROVENANCE.md` present; index SPR-01 (44 files); named in the 2026-11-12 `refs/preserved` note                                                                                | ABSORBED |
| `phenotype-cvp-audit-2026-09-14`   | dir  | 2026-09-27   | `PROVENANCE.md` present; index SPR-02 (6 files)                                                                                                                                | ABSORBED |
| `phenotype-router-monitor`         | dir  | 2026-09-16   | no `PROVENANCE.md`; no index row (the only mention is `crates/ABSORPTION_MANIFEST.md` pointing at `phenotype-tooling/absorption/`); `Cargo.toml` present                       | UNKNOWN  |
| `phenotype-router-monitor-root`    | dir  | 2026-09-16   | no `PROVENANCE.md`; no index row; no dossier; `Cargo.toml` present                                                                                                             | UNKNOWN  |
| `phenotype-router-spec`            | dir  | 2026-11-10   | `PROVENANCE.md` present; index MRG-08, 22/22                                                                                                                                   | ABSORBED |
| `ResearchLedger`                   | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-02, 318/318; `package.json` present                                                                                                         | ABSORBED |
| `resume-all`                       | dir  | 2026-09-17   | `PROVENANCE.md` present, but no `docs/ABSORPTION_INDEX.md` row and no `docs/absorbed-from/resume-all/` dossier                                                                 | PENDING  |
| `rule30-research`                  | dir  | 2026-11-10   | `PROVENANCE.md` present; index MRG-09, 6/6                                                                                                                                     | ABSORBED |
| `SessionLedger`                    | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-03, 934/934; `Cargo.toml` present                                                                                                           | ABSORBED |
| `vibeproxy-monitoring-unified`     | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-16 records EMPTY (23 refs onto one empty tree) and L5-111 RETIRE                                                                            | ABSORBED |
| `zen`                              | dir  | 2026-11-11   | `PROVENANCE.md` present; index MRG-15 (18 files, 4 branches)                                                                                                                   | ABSORBED |

Counts as of this writing, derived from the rows above: 30 entries, 24 `ABSORBED`,
3 `PENDING`, 3 `UNKNOWN`.

## The three UNKNOWN rows

`helios-bench`, `phenotype-router-monitor` and `phenotype-router-monitor-root`
each hold a tree but are not named by any disposition record in this repo. What
would settle each: a `PROVENANCE.md` or an index row naming the wave, commit and
source repository, plus a run of `python scripts/verify_absorption.py <repo>`
against that source.

## The three PENDING rows

`pheno-forge` and `resume-all` have a `PROVENANCE.md` but no index row and no
dossier, so the tree is present and self-described while the wave that placed it
is not recorded in the index. `PhenoMLX-temp` has both and is short 303 real
files by the index's own count. What would settle all three: a fresh `python
scripts/verify_absorption.py <repo>` run against a live source, with the result
appended to `docs/ABSORPTION_INDEX.md`.

## The check that re-derives this table

```bash
# the declaration the closure ledger tests
test -f absorption/STATE.md; echo $?

# re-derive the entry set: 31 paths under absorption/, of which 30 are trees
ls -1a absorption/ | tail -n +3 | wc -l                       # expect 31
ls -1a absorption/ | tail -n +3 | grep -vc '^STATE.md$'       # expect 30

# row count must equal the tree count
grep -c '^| `\?[A-Za-z.][^|]*| dir |' absorption/STATE.md      # expect 30

# provenance coverage, the main evidence column in the table
find absorption -mindepth 2 -maxdepth 2 -name PROVENANCE.md | wc -l   # expect 27

# per-tree last touch, one call per tree
ls -1a absorption/ | tail -n +3 | grep -v '^STATE.md$' \
  | xargs -I{} echo "{} $(git log -1 --format=%cs -- absorption/{})"

# the content-level check the rows point at
python scripts/verify_absorption.py --all
python scripts/scan_absorption_secrets.py absorption/
```

`scripts/verify_absorption.py` exits non-zero when a tree is genuinely short
against a live source, which is the only mechanical way to move a `PENDING` row.
An entry becomes `ABSORBED` in this file only when an index row or dossier
states the disposition and the file count that was actually copied; a row whose
evidence is absent stays `UNKNOWN` rather than being assumed.
