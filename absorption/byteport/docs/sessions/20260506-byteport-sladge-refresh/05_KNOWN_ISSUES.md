# Known Issues

- Canonical `BytePort` has unrelated local workflow, SPEC, Go module, and
  backend source edits.
- The isolated checkout emitted pre-existing LFS pointer warnings for tmp build
  artifacts.
- `go test ./...` from `backend/byteport` is blocked by local disk exhaustion
  while writing Go build artifacts.
- Frontend validation is deferred in this badge-only lane because dependencies
  may be absent and the environment is low on disk.
