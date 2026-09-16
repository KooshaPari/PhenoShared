# Testing Strategy

## Planned Checks

- `git diff --check`
- README/session badge presence search
- `git lfs status`
- Go validation with temporary build caches outside the user cache

## Results

- `git diff --check` passed.
- README/session badge presence search passed.
- `git lfs status` reported no staged or unstaged LFS objects.
- `backend/byteport`: `/opt/homebrew/bin/go test -v ./...` passed with
  `GOTOOLCHAIN=local` and temporary `GOCACHE`.
- `backend/byteport`: `/opt/homebrew/bin/go vet ./...` passed.
- `backend/byteport`: `/opt/homebrew/bin/go build -buildvcs=false ./...`
  passed after plain `go build ./...` hit VCS stamping in this worktree.
- `backend/nvms`: `/opt/homebrew/bin/go test -v ./...` still fails on
  pre-existing import cycles, provider redeclarations, and an upstream SDK
  export comment issue.

## Scope

The validation target is the backend Go stack documented in `CLAUDE.md`. The
Taskfile Cargo targets are stale for the current BytePort checkout shape.
