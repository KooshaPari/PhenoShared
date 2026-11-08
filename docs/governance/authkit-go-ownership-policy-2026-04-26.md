# AuthKit Go Ownership Policy - 2026-04-26

## Decision

`AuthKit/go` is an orphaned gitlink and must not remain in its current state.

Preferred normalization path:

1. Create or identify a real remote for the Go module.
2. Register `AuthKit/go` as a proper submodule in `AuthKit/.gitmodules`.
3. Point the parent gitlink at the nested repo's current `v0.1.0` commit.
4. Validate Go workspace state before publishing the parent pointer update.

Fallback path if no remote is created:

1. Export a bundle or patch series preserving the two nested commits.
2. Remove the nested `.git` metadata.
3. Convert `go/` into flattened source tracked directly by `AuthKit`.
4. Remove or repair `go.work` references that point at absent directories.

Do not commit the current parent `go` pointer as-is. That would only advance an
unregistered gitlink and would still be unreconstructable from a clean clone.

## Evidence

| Check | Result |
|---|---|
| Parent `AuthKit` status | ` M go` |
| Parent index entry | `160000 afa7ab9fcb60a33b9b4b9ff989f8b9624142a150 0 go` |
| Parent `.gitmodules` | Absent |
| Nested repo path | `AuthKit/go/.git` exists |
| Nested branch | `main` |
| Nested HEAD | `96355ffb29ef50bf6f0b03671b2da694a5655cfe` |
| Nested tag | `v0.1.0` |
| Nested remotes | None |
| Nested status | Clean |
| Module path | `github.com/KooshaPari/AuthKit/go` |

Nested history:

```text
96355ff chore: add initial CHANGELOG for v0.1.0 release
afa7ab9 Initial: AuthKit Go middleware package
```

## Interpretation

- It is not flattened source because parent `AuthKit` stores `go` as mode
  `160000`, so files under `go/` are not tracked by the parent repo.
- It is not a healthy submodule because no `.gitmodules` entry exists and the
  nested repo has no URL.
- It is not safe to delete or overwrite because the nested repo has a local
  `v0.1.0` commit not represented by the parent pointer.

## Risks

- Clean clones of `AuthKit` cannot reconstruct `go/` because the gitlink has no
  registered submodule URL.
- The parent points at `afa7ab9`, while the nested checkout is at `96355ff`; a
  parent-only commit would hide the changelog/tag state.
- `go.work` references `./pheno-auth`, `./pheno-crypto`, `./pheno-policy`, and
  `./pheno-secrets`, which were not present in the inspected tree.
- `middleware/middleware.go` likely needs follow-up validation before release:
  it uses JSON encoding functions but the quick inspection did not show an
  `encoding/json` import.

## Required Follow-Up Work

1. Decide remote name:
   - preferred: `<REDACTED>/authkit-go`
   - acceptable: `<REDACTED>/AuthKit-go`
   - avoid: continuing as an unregistered gitlink.
2. Push nested commits and tag to that remote.
3. Add `.gitmodules` in `AuthKit`.
4. Update parent gitlink to nested `96355ff`.
5. Run:

```bash
cd AuthKit/go
go test ./...
go list ./...
```

6. If Go validation fails, repair the Go module before parent pointer update.

## SUNSET-003 Status

Decision complete. Implementation remains gated on remote creation or explicit
approval to flatten source with a history-preserving bundle.
