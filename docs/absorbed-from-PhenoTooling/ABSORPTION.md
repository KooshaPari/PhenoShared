# Absorption Manifest — PhenoTooling (complete source port)

## Source

- **Repository:** `KooshaPari/zz-zz-agentcheck-PhenoTooling` (archived). The repo was renamed from
  `KooshaPari/PhenoTooling` during the `zz-zz-agentcheck-*` quarantine pass; the old name still redirects.
- **Revision:** `2feccc2f5b12c77785dda7960f7c31d25baf4e54` (`origin/main`)
- **Absorbed:** 2026-11-08
- **Offline backup:** `~/Exports/backups/PhenoTooling-20261104-2359-with-sweep.bundle` (404 MB). Verified on
  2026-11-08 with `git bundle list-heads` to contain 10 heads including `refs/heads/absorb-phenoUtils`
  (`3c993fea`) and `refs/stash` (`9b8d6c0c`) — the two refs that exist nowhere else.

## Target

`docs/absorbed-from-PhenoTooling/` in this repo, with each file at its **original path relative to the repo root**,
e.g. `docs/absorbed-from-PhenoTooling/docs/absorbed-from-Planify/...`.

**8 256 source files.** Selection was exact: present on `origin/main`, and **absent from the entire object graph of
both `KooshaPari/PhenoShared` and `KooshaPari/HeliosLab`** (`rev-list --objects --all`). Source extensions only
(`.rs .go .py .ts .tsx .js .swift .kt .proto`).

Largest groups:

| Group | Files |
|---|---:|
| `docs/absorbed-from-Planify` | 4 220 |
| `zz-FocalPoint/BytePort` | 997 |
| `docs/absorbed-from-heliosApp` | 550 |
| `docs/absorbed-from-phenotype-omlx` | 425 |
| `docs/absorbed-from-QuadSGM` | 297 |
| `zz-FocalPoint/AtomsBot-2nd` | 292 |
| `docs/absorbed-from-PhenoFastMCP-go` | 189 |
| `docs/absorbed-from-nanovms` | 164 |
| `docs/absorbed-from-PhenoFastMCP-rust` | 135 |

Some of these mirror repos that still exist in the org under other names (`Planify` → `zz-aa-dep-Planify`,
`heliosApp` → `heliosApp`, `BytePort` → `BytePort`, `PhenoFastMCP` → `PhenoFastMCP-archive-20261106`). They are
copied here anyway, because a mirror's continued existence is not guaranteed and this is the last pass.

Archival: not workspace members, not built, not linted. The scanners and the governance guard exclude
`docs/absorbed-from-**`.

## Status

**Absorbed.** Every source file on the source revision now exists, byte-for-byte, in a versioned GitHub-hosted
repository. Re-run the selection test to confirm zero remaining.

## Last-Resort-Exceptions

None dropped. The 8 256 files are exactly the set that was not already durable.

Non-source files (markdown, assets, lockfiles, CI configuration) are not ported here. They remain in the verified
404 MB bundle, which holds the complete history of every branch.

## Restore-Command

```bash
git clone https://github.com/KooshaPari/zz-zz-agentcheck-PhenoTooling.git
git -C zz-zz-agentcheck-PhenoTooling checkout 2feccc2f5b12c77785dda7960f7c31d25baf4e54
```

Or offline:

```bash
git clone /Users/kooshapari/Exports/backups/PhenoTooling-20261104-2359-with-sweep.bundle PhenoTooling-restored
git -C PhenoTooling-restored rev-parse refs/heads/absorb-phenoUtils   # expect 3c993fea
git -C PhenoTooling-restored rev-parse refs/stash                     # expect 9b8d6c0c
```
