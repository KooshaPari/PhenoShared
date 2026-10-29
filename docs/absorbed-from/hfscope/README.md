# hfscope

- **Source**: https://github.com/KooshaPari/zz-merge-unk-hfscope (**deleted**)
- **Declared module path**: `github.com/KooshaPari/hfscope` (**deleted**)
- **Absorbed**: 2026-09-15 (per `hfscope/PROVENANCE.md`, "Absorbed Into: PhenoMLX (`hfscope/`)")
- **Disposition**: EXCLUDE — vendored copy retained in-tree, **not** first-class
- **Location in this repo**: `hfscope/` (not `absorption/hfscope/`)
- **Canonical owner**: the external `hfscope` repository (currently deleted; no live replacement)

## Summary

A Go-based HuggingFace scope tool (~10 MB source): `internal/hfapi/` (API client),
`internal/cache/` (TTL cache), `internal/config/`, `internal/server/` (templ-rendered
web server), `internal/views/`, `hfscope-extension/` (Chrome extension), plus
`review-surface/` and a vitest/TS sidecar.

**Both declared upstreams are gone.** `git ls-remote` on
`KooshaPari/hfscope` and `KooshaPari/zz-merge-unk-hfscope` both return
"Repository not found." The in-tree copy is the only surviving snapshot, and it is
incomplete.

## Why it is excluded

- **Absorption is incomplete.** `hfscope/cmd/` does not exist, yet `go.mod`,
  `Makefile` (`PKG := ./cmd/hfscope`, `go build -o $(BIN) ./cmd/hfscope`) and
  `PROVENANCE.md` all reference `cmd/hfscope` and `cmd/hfscope-token`.
  `make build` is broken by construction and cannot be repaired from this tree.
- **`go vet` failure is a generation artifact, not a code defect.**
  `templ.Home` is undefined because `templ` is an in-repo package whose
  `*_templ.go` output is gitignored (`.gitignore:9: **/*_templ.go`). A green build
  requires `templ generate` first — a step no CI lane here runs.
- **10 files are not `gofmt`-clean**, so any `gofmt -l` gate fails immediately.
- **Wrong absorption target.** `PROVENANCE.md` declares absorption into
  PhenoMLX, yet the copy lives in PhenoShared; neither repo treats it as
  first-class.

## Action taken

- Recorded here and in `docs/ABSORPTION_INDEX.md` so module sweeps and CI
  configuration skip it permanently.
- **EXCLUDED from all CI**: no `go build`, `go vet`, `gofmt`, or `go test` lane
  may include `hfscope/`. Exclusion is by directory, not by build tag.
- **No repair attempted.** `cmd/` is unrecoverable (upstream deleted); restoring
  a build would mean authoring new code, which is not absorption.
- Tree left in place as a read-only snapshot with its `PROVENANCE.md` intact.
- Not wired into any workspace (`go.work`, Cargo workspace) — the tree is inert.

## If this is ever revived

1. Recreate the external `hfscope` repo and restore `cmd/hfscope` +
   `cmd/hfscope-token` there first.
2. Add a `templ generate` step ahead of build/vet, and commit or generate
   `*_templ.go`.
3. Run `gofmt -w` across the tree and add a `gofmt -l` gate.
4. Only then re-evaluate promotion to first-class, with a fresh disposition
   entry superseding this one.
