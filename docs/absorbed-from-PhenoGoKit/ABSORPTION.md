# Absorption Manifest — PhenoGoKit (go-sdk)

## Source

- **Repository:** `KooshaPari/PhenoGoKit` — **does not exist on GitHub** (`GET /repos/KooshaPari/PhenoGoKit` → 404)
- **Local clone used:** `repos/chat2-recovery/go-sdk/readme-git-candidate-20260912`
- **That clone's origin is a local path**, `.../chat2-recovery/go-sdk/remote-baseline`, not a remote
- **Secondary source:** `KooshaPari/PhenoTooling` `origin/main` @ `2feccc2f`, path `go-sdk/`
- **Absorbed:** 2026-11-08

## Target

`docs/absorbed-from-PhenoGoKit/` in this repo, paths relative to `go-sdk/`. Archival: not a workspace member, not
built, not linted.

**240 source files**, covering `packages/go-kit`, `packages/mcpkit`, `packages/platformkit`, `packages/devhex` and
sibling packages.

## Status

**Absorbed, because the previous plan was unsafe.** An earlier version of this audit recommended "keep standalone via
PhenoGoKit". The API shows that repo does not exist and the only local clone points at another local directory, so
"standalone" meant "one machine, no remote". That is the same failure mode that made Benchora urgent.

234 files were copied from the local clone after verifying each file's `git hash-object` equals the blob on
`PhenoTooling origin/main`. 6 files differ between the clone and PhenoTooling; those were taken from PhenoTooling so
the bytes match the audited revision. Both sets are noted because the discrepancy is real and may matter if this is
ever revived.

## Last-Resort-Exceptions

6 files under `packages/platformkit/devenv/` (`benchmarks/sandbox_test.go`, `internal/adapters/{linux,mac,windows}`,
`internal/ports/ports.go`, `internal/ports/ports_test.go`) differ between the two local sources. The PhenoTooling
revision was used. The clone's newer variants were **not** preserved — if `devenv` is revived, compare against the
clone at `chat2-recovery/go-sdk/readme-git-candidate-20260912` while it still exists.

Nothing else was dropped.

## Restore-Command

```bash
# from PhenoTooling (archived; unarchive only temporarily, immediately before use)
git clone https://github.com/KooshaPari/zz-zz-agentcheck-PhenoTooling.git
git -C zz-zz-agentcheck-PhenoTooling checkout 2feccc2f5b12c77785dda7960f7c31d25baf4e54
cp -a zz-zz-agentcheck-PhenoTooling/go-sdk/. docs/absorbed-from-PhenoGoKit/

# or from the local clone that still exists on this machine
cp -a ~/CodeProjects/Phenotype/repos/chat2-recovery/go-sdk/readme-git-candidate-20260912/packages/. \
      docs/absorbed-from-PhenoGoKit/packages/
```
