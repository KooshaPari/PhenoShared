# Known Issues

## Superseded Branch

The older `docs/byteport-sladge-current` branch at `691049c7` diverged from
current canonical head and should be treated as stale evidence after this
refresh.

## LFS Checkout Artifacts

A normal worktree checkout produced non-pointer LFS artifacts under
`backend/byteport/tmp/`. The refresh worktree was recreated with
`GIT_LFS_SKIP_SMUDGE=1` to keep the intended change isolated.

## Backend Go Build Blocker

`GOCACHE=/tmp/byteport-go-build-cache go test -v ./...` from
`backend/byteport` runs library tests successfully but fails the root package
build because `main.go` has pre-existing unused imports:

- `go.opentelemetry.io/otel/attribute`
- `go.opentelemetry.io/otel/sdk/resource`
