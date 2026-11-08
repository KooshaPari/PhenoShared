# Absorption Manifest — PhenoTooling

## Source

- **Repository:** `KooshaPari/PhenoTooling` (currently archived)
- **Revision audited:** `2feccc2f5b12c77785dda7960f7c31d25baf4e54` (`origin/main`)
- **Local-only refs:** `absorb-phenoUtils` (`3c993fea`), stash `9b8d6c0c`
- **Also present:** `chore/redaction-and-artifact-sweep` (`f0e0fbd8`), two `security/*` branches, tag `phinbox-v0.9.0`
- **Only full backup:** `~/Exports/backups/PhenoTooling-20261104-2359-with-sweep.bundle` (404 MB, 10 heads)

## Target

Absorption is distributed, because PhenoTooling was a merge staging area rather than a single product.

| What | Destination | State |
|---|---|---|
| 16 PhenoCompose crates | `crates/pheno-compose-*` (this repo) | absorbed earlier, `35fe8a24` |
| 41 non-crate PhenoCompose files | `docs/absorbed-from-PhenoCompose/` (this repo) | **absorbed 2026-11-08** |
| 13-file `bin/` deletion-gate tooling | `bin/` (this repo) | restored |
| `quinn-proto 0.11.19` | `Cargo.lock` (this repo) | restored, `3f17d8f8` |
| GUI answer coercion | `crates/phinbox/src/spec/coerce.rs` | live path already existed and was **better**; the ported duplicate in `platform/macos/parse.rs` was deleted 2026-11-08 |
| `zz-PhenoObservability` (139 source files) | `KooshaPari/PhenoObservability` | present by path (741 files, pushed) |
| `go-sdk` (229 source files) | `KooshaPari/PhenoGoKit` | byte-identical in the local clone |
| `Benchora` (138 files) | `KooshaPari/HeliosLab`, `benchora/` | **folded 2026-11-08** (HeliosLab PR #245) |
| `Eventra` crates | PhenoShared history, `archives/Eventra-rb/` | absorbed 2026-11-05 |
| `zz-Configra` | already present in PhenoShared | never lost |

## Status

**Deletion-eligible once the two open PRs are merged.** Not yet deletable.

Evidence: 2 183 candidate files; 558 byte-identical in PhenoShared `HEAD`; 1 625 absent; 584 of those source;
**467 absent from PhenoShared's entire object graph**; of those, **381 have a byte-identical copy in another local
repo**. The residual 86 resolved as: 41 PhenoCompose (absorbed here), 29 Benchora (folded into HeliosLab), 11 authkit
(already under `docs/absorbed-from-authkit`), 5 observability files (present by path in `PhenoObservability`).

Two conditions remain:

1. **Merge the PhenoCompose port and the Benchora fold.** Until merged, that content exists only on branches.
2. **Keep the bundle** until both merges are on `main`.

Then re-run `bin/repo-delete-gate.sh --repo KooshaPari/PhenoTooling` with **no `--force`**.

## Last-Resort-Exceptions

- **`refs/heads/absorb-phenoUtils` is pushed nowhere.** It survives only in the local clone and the bundle. The
  bundle was verified 2026-11-08 to contain it (`3c993fea`) and `refs/stash` (`9b8d6c0c`).
- **The stash tree holds 20 paths** absent from PhenoTooling `origin/main` and `HEAD`. All 20 were subsequently found
  to **already exist in PhenoShared `HEAD`** (0 absent by path): older revisions of live files, not lost files.
  Recorded so nobody re-derives a false alarm.
- **`Eventra` is out of scope here.** Its 44 branches hold 289 blobs that exist in no other local repo; separate
  preservation problem.
- **No repository was deleted during this audit.** A validation worker attempted a forced delete against
  `KooshaPari/test` (HTTP 404, exit 1, `delete_repo` scope absent). Nothing was confirmed deleted; the attempt is
  recorded because a 404 cannot distinguish "never existed" from "not visible".
- **Unarchiving is not required** for any precondition, and must not be done except temporarily, immediately before
  deletion.

## Restore-Command

Online:

```bash
git clone https://github.com/KooshaPari/PhenoTooling.git
```

Offline, from the only full backup:

```bash
git clone /Users/kooshapari/Exports/backups/PhenoTooling-20261104-2359-with-sweep.bundle PhenoTooling-restored
git -C PhenoTooling-restored rev-parse refs/heads/absorb-phenoUtils   # expect 3c993fea
git -C PhenoTooling-restored rev-parse refs/stash                     # expect 9b8d6c0c
```
